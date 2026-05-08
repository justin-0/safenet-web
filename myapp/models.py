from django.db import models
from django.contrib.auth.models import User


class Authority(models.Model):
    USER = models.OneToOneField(User, on_delete=models.CASCADE)
    photo1 = models.FileField(upload_to='authority_photo', null=True, blank=True)
    name = models.CharField(max_length=200)
    email = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    place = models.CharField(max_length=200)
    license_proof = models.FileField(upload_to='authority_license')


class Resident(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]

    USER = models.OneToOneField(User, on_delete=models.CASCADE)
    photo1 = models.FileField(upload_to='resident_photo', null=True, blank=True)
    name = models.CharField(max_length=200)
    gender = models.CharField(max_length=20)
    dob = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.CharField(max_length=100)
    house_number = models.CharField(max_length=100)
    latitude = models.CharField(max_length=100)
    longitude = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

class Category(models.Model):
    category_name = models.CharField(max_length=200)


class Worker(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]

    USER = models.OneToOneField(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    photo1 = models.FileField(upload_to='worker_photo', null=True, blank=True)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)
    email = models.CharField(max_length=100)
    address = models.TextField()
    id_proof = models.FileField(upload_to='worker_id', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')


class Complaint(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('replied', 'Replied')
    ]

    sender = models.ForeignKey(Resident, on_delete=models.CASCADE)
    receiver = models.ForeignKey(Authority, on_delete=models.CASCADE)
    complaint = models.TextField()
    complaint_date = models.CharField(max_length=100)
    reply = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')


class WorkerRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected')
    ]

    RESIDENT = models.ForeignKey(Resident, on_delete=models.CASCADE)
    WORKER = models.ForeignKey(Worker, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_requested')
    date = models.CharField(max_length=100)


class FamilyMember(models.Model):
    RESIDENT = models.ForeignKey(Resident, on_delete=models.CASCADE)
    photo1 = models.FileField(upload_to='familymember_photo', null=True, blank=True)
    name = models.CharField(max_length=200)
    gender = models.CharField(max_length=20)
    age = models.CharField(max_length=15)
    relationship = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)


class Chat(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sender')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_receiver')
    message = models.TextField()
    hate_speech_flag = models.BooleanField(default=False)
    date = models.CharField(max_length=100)


class StrayDogAlert(models.Model):
    RESIDENT = models.ForeignKey(Resident, on_delete=models.CASCADE)
    latitude = models.CharField(max_length=100)
    longitude = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='stray_dog_alerts/', null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)


class EmergencyAlert(models.Model):
    ALERT_TYPE = [
        ('panic', 'Panic Button'),
        ('volume', 'Volume Button'),
        ('shake', 'Shake Detection')
    ]

    RESIDENT = models.ForeignKey(Resident, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE)
    latitude = models.CharField(max_length=100)
    longitude = models.CharField(max_length=100)
    date = models.CharField(max_length=100)



class Camera(models.Model):
    camera_name = models.CharField(max_length=200)
    latitude = models.CharField(max_length=100)
    longitude = models.CharField(max_length=100)


class UnauthorizedEntry(models.Model):
    camera = models.ForeignKey(Camera,on_delete=models.CASCADE)
    image = models.FileField(upload_to='unauthorized_faces')
    detected_time = models.CharField(max_length=100)