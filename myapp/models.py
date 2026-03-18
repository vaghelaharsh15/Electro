from django.db import models
from django.utils import timezone
# Create your models here.
from django.core.validators import MinLengthValidator
from django.conf import settings



class AppUser(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phoneno = models.CharField(max_length=20, unique=True)
    password = models.CharField(max_length=128)  # stores hashed password
    profile_image = models.ImageField(upload_to="profile_pics", null=True, blank=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Color(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True, blank=True)
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="products")
    date=models.DateField(null=True,blank=True,default=timezone.now)
    discription=models.TextField(null=True,blank=True)
    stock=models.IntegerField(default=20)

    def __str__(self):
        return self.name

    # Backwards-compatible aliases for existing templates
    @property
    def product_name(self):
        return self.name

    @property
    def product_image(self):
        return self.image

class Contact(models.Model):
    code=models.CharField(max_length=3,validators=[MinLengthValidator(1)])
    contact_number=models.CharField(max_length=12,validators=[MinLengthValidator(10)])
    contact_email=models.EmailField(null=True,blank=True,max_length=40)
    address=models.CharField(max_length=60,null=True,blank=True)
    def __str__(self):
        return self.contact_number
    
class Cart(models.Model):
    user = models.ForeignKey(AppUser,on_delete=models.CASCADE,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def cart_total(self):
        return sum(item.total_price() for item in self.items.all())

    def __str__(self):
        return f"Cart of {self.user.name}"

class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, 
        related_name="items", 
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    def total_price(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"


class Wishlist(models.Model):
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="wishlists")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wishlist of {self.user.name}"


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("wishlist", "product")

    def __str__(self):
        return f"{self.product.name} in {self.wishlist}"


class CompareList(models.Model):
    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="compare_lists")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CompareList of {self.user.name}"


class CompareItem(models.Model):
    compare_list = models.ForeignKey(CompareList, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("compare_list", "product")

    def __str__(self):
        return f"{self.product.name} in compare"

# class Coupon(models.Model):
#     user=models.ForeignKey(AppUser,on_delete=models.CASCADE)
#     name=models.CharField(max_length=30)
#     eligible=models.TextField()
#     price_off=models.PositiveIntegerField()
#     active=models.BooleanField()

#     def __str__(self):
#         return self.name

class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discription=models.TextField(null=True,blank=True)
    discount = models.IntegerField(help_text="Discount percentage")
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    min_ammount=models.IntegerField(null=True,blank=True)

    def __str__(self):
        return self.code


class ContactMsg(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    project = models.CharField(max_length=200)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    user=models.ForeignKey(AppUser,on_delete=models.CASCADE,null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
    ]

    user = models.ForeignKey(AppUser, on_delete=models.CASCADE, related_name="orders")

    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=120)
    country = models.CharField(max_length=120)
    postcode = models.CharField(max_length=30)
    mobile = models.CharField(max_length=20)
    email = models.EmailField()
    order_notes = models.TextField(blank=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} ({self.status})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"OrderItem(order={self.order_id}, product={self.product_id})"
    