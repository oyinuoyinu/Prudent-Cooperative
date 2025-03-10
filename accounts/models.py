from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db.models.fields.related import ForeignKey, OneToOneField

# from django.contrib.gis.db import models as gismodels
# from django.contrib.gis.geos import Point


class UserManager(BaseUserManager):

    def create_user(self, first_name, last_name, username, email, password=None):
        if not email:
            raise ValueError('Email is required')

        if not username:
            raise ValueError('Username is required')

        user = self.model(
            email = self.normalize_email(email),
            username = username,
            first_name = first_name,
            last_name = last_name,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, first_name, last_name, username, email, password=None):
        user = self.create_user(
            email = self.normalize_email(email),
            username = username,
            password = password,
            first_name = first_name,
            last_name = last_name,
        )
        user.is_admin = True
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):

    # This code defines the `User` model with various fields such as `first_name`, `last_name`,
    # `username`, `email`, `role`, `date_joined`, `last_login`, `created_date`, `modified_date`,
    # `is_admin`, `is_staff`, `is_active`, `is_superuser`, and `password`.

    MEMBER = 1
    ADMIN = 2


    ROLE_CHOICE = (
        (MEMBER, 'Member'),
        (ADMIN, 'Admin'),

    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=100, unique=True)
    role = models.PositiveSmallIntegerField(choices=ROLE_CHOICE, blank=True, null=True)

     # required fields
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now_add=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    password = models.CharField(max_length=100)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta(AbstractBaseUser.Meta):
        swappable = 'AUTH_USER_MODEL'


    objects = UserManager()
    """
        This is a class that defines methods for user permissions and role identification.
        :return: The `__str__` method returns the email of the user object. The `has_perm` method returns
        a boolean value indicating whether the user is an admin or not. The `has_module_perms` method
        always returns True. The `get_role` method returns a string indicating the role of the user
        object, which can be "Member", "Admin", or "Manager" depending on the value
    """

    def __str__(self):
        return self.first_name + ' ' + self.last_name

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return True

    def get_role(self):
        """
        The function returns the role of a user based on their assigned role number.
        :return: the role of the user as a string, which can be either 'Member', 'Admin', or
        'Manager', based on the value of the 'role' attribute of the object.
        """
        if self.role == 1:
            user_role = 'Member'
        elif self.role == 2:
            user_role = 'Admin'
        elif self.role == 3:
            user_role = 'Manager'
        return user_role


class UserProfile(models.Model):

   # This code defines a `UserProfile` model with various fields such as `user`, `profile_picture`,
   # `phone_number`, `address`, `country`, `state`, `city`, `created_at`, and `modified_at`.

    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='users/profile_pictures', blank=True, null=True)
    phone_number = models.CharField(max_length=11, blank=True)
    address = models.CharField(max_length=250, blank=True, null=True)
    country = models.CharField(max_length=15, blank=True, null=True)
    state = models.CharField(max_length=15, blank=True, null=True)
    city = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    #location = gismodels.PointField(blank=True, null=True, srid=4326)


    # def full_address(self):
    #     return f'{self.address_line_1}, {self.address_line_2}'

    def __str__(self):
        return self.user.email

    # def save(self, *args, **kwargs):
        # if self.latitude and self.longitude:
            # self.location = Point(float(self.longitude), float(self.latitude))
            # return super(UserProfile, self).save(*args, **kwargs)
        # return super(UserProfile, self).save(*args, **kwargs)
