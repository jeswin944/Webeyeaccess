from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class User_profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    First_name = models.CharField(max_length=100)
    Last_name = models.CharField(max_length=100)
    place = models.CharField(max_length=100)
    Email = models.EmailField(max_length=100)
    Phone_number = models.CharField(max_length=15)
    Gender = models.CharField(max_length=10)

class complaints(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    Title = models.CharField(max_length=100)
    Description = models.TextField()
    reply = models.TextField(blank=True, null=True)
    Date = models.DateTimeField(auto_now_add=True)

class feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    Feedback = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
