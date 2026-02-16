from django.db import models
from django.utils import timezone
# Create your models here.
from django.core.validators import MinLengthValidator


class AppUser(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phoneno = models.CharField(max_length=20, unique=True)
    password = models.CharField(max_length=128)  # stores hashed password

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
    
