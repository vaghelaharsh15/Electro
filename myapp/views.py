from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import *
from django.db.models import Count
from django.db.models import Q
from decimal import Decimal, InvalidOperation
from django.contrib.auth.hashers import make_password, check_password


def _parse_decimal(value: str | None):
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def _filtered_products_context(request):
    products = Product.objects.all()

    category_ids = request.GET.getlist("category")
    category_param = request.GET.get("category") or request.GET.get("category_name")
    color_param = request.GET.get("color") or request.GET.get("color_name")
    min_price = _parse_decimal(request.GET.get("min_price"))
    max_price = _parse_decimal(request.GET.get("max_price"))

    # category filter: multiple (checkboxes) or single (links)
    selected_category_ids = set()
    if category_ids:
        valid_ids = [int(cid) for cid in category_ids if str(cid).strip().isdigit()]
        if valid_ids:
            selected_category_ids = set(valid_ids)
            products = products.filter(category_id__in=valid_ids)
    elif category_param:
        category_param = str(category_param).strip()
        if category_param.isdigit():
            products = products.filter(category_id=int(category_param))
            selected_category_ids = {int(category_param)}
        else:
            products = products.filter(category__name__iexact=category_param)

    # color filter (supports id or name)
    if color_param:
        color_param = str(color_param).strip()
        if color_param.isdigit():
            products = products.filter(color_id=int(color_param))
        else:
            products = products.filter(color__name__iexact=color_param)

    # price filter
    if min_price is not None:
        products = products.filter(price__gte=min_price)
    if max_price is not None:
        products = products.filter(price__lte=max_price)

    categories = Category.objects.annotate(count=Count("product"))
    colors = Color.objects.annotate(count=Count("product"))

    return {
        "products": products,
        "pid": products,  # template expects `pid`
        "categories": categories,
        "colors": colors,
        "selected_category": category_param or "",
        "selected_category_ids": selected_category_ids,
        "selected_color": color_param or "",
        "min_price": "" if min_price is None else str(min_price),
        "max_price": "" if max_price is None else str(max_price),
    }

def product_list(request):
    # Keep /products/ working; use the existing shop template + filtering sidebar.
    context = _filtered_products_context(request)
    return render(request, "shop.html", context)







# Create your views here.
def index(request):
    products = Product.objects.all()
    categories = Category.objects.annotate(count=Count("product"))
    return render(request, "index.html", {"products": products, "categories": categories})
    # return render(request,"index.html")

def shop(request):
    context = _filtered_products_context(request)
    return render(request, "shop.html", context)
def single(request):
    return render(request,"single.html")

def bestseller(request):
    return render(request,"bestseller.html")

def _get_cart(request):
    """Get cart from session (list of dicts: name, model, price, quantity)."""
    if 'cart' not in request.session:
        request.session['cart'] = []
    raw = request.session['cart']
    # Ensure all items are dicts (filter out corrupted/old-format entries)
    valid = [x for x in raw if isinstance(x, dict)]
    if len(valid) != len(raw):
        request.session['cart'] = valid
        request.session.modified = True
    return request.session['cart']

def add_to_cart(request):
    if request.method != 'POST':
        return redirect('cart')
    name = request.POST.get('name', 'Product').strip()
    price = request.POST.get('price', '0').strip()
    model = request.POST.get('model', '').strip()
    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        quantity = 1
    if quantity < 1:
        quantity = 1
    try:
        price_float = float(price.replace(',', ''))
    except ValueError:
        price_float = 0.0
    cart = _get_cart(request)
    # Match by name + model to update quantity (only dict items)
    for item in cart:
        if not isinstance(item, dict):
            continue
        if item.get('name') == name and item.get('model') == model:
            item['quantity'] = item.get('quantity', 0) + quantity
            break
    else:
        cart.append({
            'name': name,
            'model': model,
            'price': price_float,
            'quantity': quantity,
        })
    request.session.modified = True
    return redirect('cart')

def remove_from_cart(request):
    if request.method != 'POST':
        return redirect('cart')
    try:
        index = int(request.POST.get('index', -1))
    except ValueError:
        return redirect('cart')
    cart = _get_cart(request)
    if 0 <= index < len(cart):
        cart.pop(index)
        request.session.modified = True
    return redirect('cart')

def cart(request):
    cart_items = _get_cart(request)
    # Only process dict items (ignore corrupted/old session data)
    valid_items = [item for item in cart_items if isinstance(item, dict)]
    for item in valid_items:
        item['total'] = item.get('price', 0) * item.get('quantity', 0)
    cart_total = sum(item['total'] for item in valid_items)
    return render(request, "cart.html", {
        'cart_items': valid_items,
        'cart_total': cart_total,
    })

def cheackout(request):
    return render(request,"cheackout.html")

def error(request):
    return render(request,"404.html")

def contact(request):
    return render(request,"contact.html")


def register(request):
    error = None
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phoneno = request.POST.get('phoneno', '').strip()
        password = request.POST.get('password', '')
        confirmpassword = request.POST.get('confirmpassword', '')
        if not name or not email or not phoneno or not password or not confirmpassword:
            error = "All fields are required."
        elif password != confirmpassword:
            error = "Password and Confirm Password do not match."
        elif AppUser.objects.filter(email=email).exists():
            error = "Email already registered."
        elif AppUser.objects.filter(phoneno=phoneno).exists():
            error = "Phone number already registered."
        else:
            AppUser.objects.create(
                name=name,
                email=email,
                phoneno=phoneno,
                password=make_password(password),
            )
            return redirect('login')
    return render(request, "register.html", {"error": error})


def login(request):
    error = None
    if request.method == 'POST':
        email_or_phone = request.POST.get('email_or_phone', '').strip()
        password = request.POST.get('password', '')
        if not email_or_phone or not password:
            error = "Email/Phone and Password are required."
        else:
            user = AppUser.objects.filter(
                Q(email=email_or_phone) | Q(phoneno=email_or_phone)
            ).first()
            if user and check_password(password, user.password):
                request.session['user_id'] = user.id
                request.session['user_name'] = user.name
                return redirect('index')
            else:
                error = "Invalid email/phone or password."
    return render(request, "login.html", {"error": error})


def logout(request):
    request.session.pop('user_id', None)
    request.session.pop('user_name', None)
    return redirect('index')


