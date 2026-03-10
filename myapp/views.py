from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import *
from django.db.models import Count
from django.db.models import Q
from decimal import Decimal, InvalidOperation
from django.contrib.auth.hashers import make_password, check_password
from django.db.models.functions import Random
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
import random, time
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User




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
    if "user_id" in request.session:
        user_name = request.session.get("user_name")
    else:
        user_name = "Welcome please Login"

    products = Product.objects.all()
    contacts=Contact.objects.first()
    category_ids = request.GET.getlist("category")
    category_param = request.GET.get("category") or request.GET.get("category_name")
    color_param = request.GET.get("color") or request.GET.get("color_name")
    min_price = _parse_decimal(request.GET.get("min_price"))
    max_price = _parse_decimal(request.GET.get("max_price"))
    search=request.GET.get("search")
    
    if search:
        products=products.filter(Q(name__icontains=search)|Q(category__name__icontains=search)|Q(brand__name__icontains=search)|Q(color__name__icontains=search))
    
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
    paginator = Paginator(products, 12)
    page_number = request.GET.get("page",1)
    try:
        page_number = int(page_number)
    except ValueError:
        page_number = 1 
    products = paginator.get_page(page_number)
    show_page=paginator.get_elided_page_range(page_number,on_each_side=1,on_ends=1)
    get_copy = request.GET.copy()
    if "page" in get_copy:
        del get_copy["page"]
    query_string = get_copy.urlencode()
    # Wishlist info for current user
    wishlist_ids, wishlist_count = _wishlist_ids_and_count(request)

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
        "contacts": contacts,
        "show_page": show_page,
        "query_string": query_string,
        "user_name": user_name,
        "wishlist_ids": wishlist_ids,
        "wishlist_count": wishlist_count,
    }


def _wishlist_ids_and_count(request):
    """Return (product_id_list, count) for the logged-in AppUser's wishlist."""
    user_id = request.session.get("user_id")
    if not user_id:
        return [], 0
    try:
        app_user = AppUser.objects.get(id=user_id)
    except AppUser.DoesNotExist:
        return [], 0
    wishlist = Wishlist.objects.filter(user=app_user).first()
    if not wishlist:
        return [], 0
    ids = list(
        wishlist.items.values_list("product_id", flat=True)
    )
    return ids, len(ids)

def product_list(request):
    # Keep /products/ working; use the existing shop template + filtering sidebar.
    context = _filtered_products_context(request)
    return render(request, "shop.html", context)







# Create your views here.
def index(request):
    contacts = Contact.objects.first()
    products = Product.objects.all()
    new_arrivals_products = Product.objects.all().order_by('-date')
    categories = Category.objects.annotate(count=Count("product"))    
    paginator = Paginator(products,12)
    page_number = request.GET.get("page",1)
    if "user_id" in request.session:
        user_name = request.session.get("user_name")
    else:
        user_name = "Welcome please Login"
    # print(user_name)

    try:
        page_number = int(page_number)
    except ValueError:
        page_number = 1 
    products = paginator.get_page(page_number)
    show_page = paginator.get_elided_page_range(page_number, on_each_side=1, on_ends=1)

    wishlist_ids, wishlist_count = _wishlist_ids_and_count(request)

    return render(request, "index.html", {
        "contacts": contacts,
        "products": products,
        "new_arrivals_products": new_arrivals_products,
        "categories": categories,
        "show_page": show_page,
        "user_name": user_name,
        "wishlist_ids": wishlist_ids,
        "wishlist_count": wishlist_count,
    })
    # return render(request,"index.html")

def shop(request):
    context= _filtered_products_context(request)
    return render(request, "shop.html",context)
def single(request):
    if "user_id" in request.session:
        user_name = request.session.get("user_name")
    else:
        user_name = "Welcome please Login"
    id = request.GET.get("product")
    product = Product.objects.order_by('-date').first()
    if id:
        product = get_object_or_404(Product, id=id)
    related_products = Product.objects.filter(category=product.category)
    categories = Category.objects.annotate(count=Count("product"))
    contacts=Contact.objects.first()
    colors = Color.objects.annotate(count=Count("product"))

    wishlist_ids, wishlist_count = _wishlist_ids_and_count(request)
    return render(request,"single.html",{
        "contacts": contacts,
        "categories": categories,
        "user_name": user_name,
        "product": product,
        "colors": colors,
        "related_products": related_products,
        "wishlist_ids": wishlist_ids,
        "wishlist_count": wishlist_count,
        })

def bestseller(request):
    if "user_id" in request.session:
        user_name = request.session.get("user_name")
    else:
        user_name = "Welcome please Login"
    products = Product.objects.order_by(Random())
    contacts = Contact.objects.first()
    categories = Category.objects.annotate(count=Count("product"))
    new_arrivals_products = Product.objects.order_by('-date')[:8]

    wishlist_ids, wishlist_count = _wishlist_ids_and_count(request)
    return render(request, "bestseller.html", {
        "contacts": contacts,
        "products": products,
        "categories": categories,
        "new_arrivals_products": new_arrivals_products,
        "user_name": user_name,
        "wishlist_ids": wishlist_ids,
        "wishlist_count": wishlist_count,
    })

def toggle_wishlist(request, product_id):
    """Add/remove a product from the logged-in AppUser's wishlist."""
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    try:
        app_user = AppUser.objects.get(id=user_id)
    except AppUser.DoesNotExist:
        request.session.pop("user_id", None)
        request.session.pop("user_name", None)
        return redirect("login")

    product = get_object_or_404(Product, id=product_id)
    wishlist, _ = Wishlist.objects.get_or_create(user=app_user)
    existing = WishlistItem.objects.filter(wishlist=wishlist, product=product)
    if existing.exists():
        existing.delete()
    else:
        WishlistItem.objects.create(wishlist=wishlist, product=product)

    # Go back where we came from, or to wishlist page
    return redirect(request.META.get("HTTP_REFERER") or "wishlist")


def wishlist(request):
    """Show all wishlisted items for the logged-in AppUser."""
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    try:
        app_user = AppUser.objects.get(id=user_id)
    except AppUser.DoesNotExist:
        request.session.pop("user_id", None)
        request.session.pop("user_name", None)
        return redirect("login")

    contacts = Contact.objects.first()
    categories = Category.objects.annotate(count=Count("product"))
    wishlist_obj = Wishlist.objects.filter(user=app_user).first()
    if wishlist_obj:
        items = wishlist_obj.items.select_related("product")
    else:
        items = []

    wishlist_ids, wishlist_count = _wishlist_ids_and_count(request)

    return render(request, "wishlist.html", {
        "contacts": contacts,
        "categories": categories,
        "user_name": request.session.get("user_name") or app_user.name,
        "wishlist_items": items,
        "wishlist_ids": wishlist_ids,
        "wishlist_count": wishlist_count,
    })

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

# def add_to_cart(request):
    # if request.method != 'POST':
    #     return redirect('cart')
    # name = request.POST.get('name', 'Product').strip()
    # price = request.POST.get('price', '0').strip()
    # model = request.POST.get('model', '').strip()
    # try:
    #     quantity = int(request.POST.get('quantity', 1))
    # except ValueError:
    #     quantity = 1
    # if quantity < 1:
    #     quantity = 1
    # try:
    #     price_float = float(price.replace(',', ''))
    # except ValueError:
    #     price_float = 0.0
    # cart = _get_cart(request)
    # # Match by name + model to update quantity (only dict items)
    # for item in cart:
    #     if not isinstance(item, dict):
    #         continue
    #     if item.get('name') == name and item.get('model') == model:
    #         item['quantity'] = item.get('quantity', 0) + quantity
    #         break
    # else:
    #     cart.append({
    #         'name': name,
    #         'model': model,
    #         'price': price_float,
    #         'quantity': quantity,
    #     })
    # request.session.modified = True
    # return redirect('cart')
def add_to_cart(request, product_id=None):
    """
    Add a product to the logged-in AppUser's cart (DB-backed).
    Supports:
    - GET /add_to_cart/<product_id>/ (links)
    - POST /add_to_cart/ with product_id in form
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    try:
        app_user = AppUser.objects.get(id=user_id)
    except AppUser.DoesNotExist:
        request.session.pop("user_id", None)
        request.session.pop("user_name", None)
        return redirect("login")

    pid = product_id
    if pid is None:
        pid = request.POST.get("product_id") or request.GET.get("product_id") or request.GET.get("product")
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return redirfect("cart")

    product = get_object_or_404(Product, id=pid_int)

    # Quantity (POST supported; links default to 1)
    quantity = 1
    if request.method == "POST":
        try:
            quantity = int(request.POST.get("quantity", 1))
        except ValueError:
            quantity = 1
        if quantity < 1:
            quantity = 1

    cart, _ = Cart.objects.get_or_create(user=app_user)
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={"quantity": quantity, "price": product.price},
    )
    if not created:
        item.quantity = item.quantity + quantity
        item.price = product.price
        item.save()

    return redirect("cart")


def update_cart(request, item_id, action):
    """Increase/decrease quantity for a cart item of logged-in AppUser."""
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    try:
        app_user = AppUser.objects.get(id=user_id)
    except AppUser.DoesNotExist:
        request.session.pop("user_id", None)
        request.session.pop("user_name", None)
        return redirect("login")

    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=app_user)

    if action == "increase":
        cart_item.quantity += 1
        cart_item.save()
    elif action == "decrease":
        cart_item.quantity -= 1
        if cart_item.quantity <= 0:
            cart_item.delete()
        else:
            cart_item.save()

    return redirect("cart")


def remove_from_cart(request, item_id=None):
    """Remove a cart item for logged-in AppUser (supports POST form or URL param)."""
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    try:
        app_user = AppUser.objects.get(id=user_id)
    except AppUser.DoesNotExist:
        request.session.pop("user_id", None)
        request.session.pop("user_name", None)
        return redirect("login")

    iid = item_id
    if iid is None:
        iid = request.POST.get("item_id")
    try:
        iid_int = int(iid)
    except (TypeError, ValueError):
        return redirect("cart")

    CartItem.objects.filter(id=iid_int, cart__user=app_user).delete()
    return redirect("cart")


def cart(request):
    """Show logged-in AppUser cart."""
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    try:
        app_user = AppUser.objects.get(id=user_id)
    except AppUser.DoesNotExist:
        request.session.pop("user_id", None)
        request.session.pop("user_name", None)
        return redirect("login")

    categories = Category.objects.annotate(count=Count("product"))
    contacts = Contact.objects.first()

    cart_obj = Cart.objects.filter(user=app_user).first()
    if not cart_obj:
        cart_items = []
        cart_total = 0
    else:
        cart_items = list(cart_obj.items.select_related("product").all())
        cart_total = sum((ci.total_price() for ci in cart_items), Decimal("0"))

    return render(request, "cart.html", {
        "contacts": contacts,
        "cart_items": cart_items,
        "cart_total": cart_total,
        "categories": categories,
        "user_name": request.session.get("user_name") or app_user.name,
    })

def cheackout(request):
    if "user_id" in request.session:
        contacts=Contact.objects.first()
        user_name=request.session.get("user_name") 
        categories = Category.objects.annotate(count=Count("product"))
        return render(request,"cheackout.html",{"contacts":contacts,"categories":categories,"user_name":user_name})
    else:
        return redirect("login")

def error(request):
    if "user_id" in request.session:
        user_name=request.session.get("user_name")  
    else:
        user_name="Welcome please Login"
    contacts=Contact.objects.first()
    categories = Category.objects.annotate(count=Count("product"))
    return render(request,"404.html",{"contacts":contacts,"categories":categories,"user_name":user_name})

def contact(request):
    if "user_id" in request.session:
        contacts=Contact.objects.first()
        user_name=request.session.get("user_name") 
        categories = Category.objects.annotate(count=Count("product"))
        return render(request,"contact.html",{"contacts":contacts,"categories":categories,"user_name":user_name})
    else:
        return redirect("login")

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


def profile(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    try:
        user = AppUser.objects.get(id=user_id)
    except AppUser.DoesNotExist:
        request.session.pop('user_id', None)
        request.session.pop('user_name', None)
        return redirect('login')
    error = None
    success = None
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phoneno = request.POST.get('phoneno', '').strip()
        profile_image = request.FILES.get('profile_image')
        if not name or not email or not phoneno:
            error = "Name, email and phone are required."
        elif AppUser.objects.filter(email=email).exclude(id=user.id).exists():
            error = "Email already in use."
        elif AppUser.objects.filter(phoneno=phoneno).exclude(id=user.id).exists():
            error = "Phone number already in use."
        else:
            user.name = name
            user.email = email
            user.phoneno = phoneno
            if profile_image:
                user.profile_image = profile_image
            user.save()
            request.session['user_name'] = user.name
            success = "Profile updated successfully."
    return render(request, "profile.html", {"user": user, "error": error, "success": success})

import random
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.shortcuts import render, redirect

def forgot(request):
    context = {}

    if request.method == "POST":

        # -------- SEND OTP --------
        if "send_otp" in request.POST:
            email = request.POST.get("email", "").strip()

            if not email:
                context["error"] = "Email is required"
                return render(request, "forgot.html", context)

            if not AppUser.objects.filter(email=email).exists():
                context["error"] = "Email not registered"
                return render(request, "forgot.html", context)

            otp = random.randint(100000, 999999)

            request.session["reset_email"] = email
            request.session["reset_otp"] = str(otp)
            request.session["otp_time"] = time.time()

            send_mail(
                "Password Reset OTP",
                f"Your OTP is {otp}",
                settings.EMAIL_HOST_USER,
                [email],
            )

            context["message"] = "OTP sent to your email"
            context["otp_sent"] = True
            return render(request, "forgot.html", context)

        # -------- VERIFY OTP --------
        if "verify_otp" in request.POST:
            entered_otp = request.POST.get("otp", "").strip()
            new_password = request.POST.get("new_password", "")
            confirm_password = request.POST.get("confirm_password", "")

            session_otp = request.session.get("reset_otp")
            email = request.session.get("reset_email")
            otp_time = request.session.get("otp_time")

            if not (session_otp and email and otp_time):
                context["error"] = "OTP session expired. Please request a new OTP."
                return render(request, "forgot.html", context)

            # OTP expiry check (5 minutes)
            if time.time() - otp_time > 300:
                context["error"] = "OTP expired. Please request a new OTP."
                return render(request, "forgot.html", context)

            if entered_otp != session_otp:
                context["error"] = "Invalid OTP"
                context["otp_sent"] = True
                return render(request, "forgot.html", context)

            if not new_password or new_password != confirm_password:
                context["error"] = "Passwords do not match"
                context["otp_sent"] = True
                return render(request, "forgot.html", context)

            try:
                user = AppUser.objects.get(email=email)
            except AppUser.DoesNotExist:
                context["error"] = "User not found"
                return render(request, "forgot.html", context)

            user.password = make_password(new_password)
            user.save()

            # Clear reset-related session keys
            for key in ("reset_email", "reset_otp", "otp_time"):
                if key in request.session:
                    del request.session[key]

            context["message"] = "Password reset successful. You can now login."
            return render(request, "forgot.html", context)

    return render(request, "forgot.html", context)
    