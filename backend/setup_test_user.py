from user.models import User
user = User.objects.get(email="emmbamp@gmail.com")
user.set_password("password123")
user.save()
print(f"✅ Password set for {user.email}")
