import argparse
import os
import django


def main():
    parser = argparse.ArgumentParser(description="Create a manager account.")
    parser.add_argument("--username", required=True, help="login username")
    parser.add_argument("--password", required=True, help="login password")
    parser.add_argument("--name", required=True, help="display name")
    args = parser.parse_args()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()

    from django.contrib.auth.models import User
    from users.models import UserProfile

    if User.objects.filter(username__iexact=args.username).exists():
        raise SystemExit("username already exists")

    user = User.objects.create_user(
        username=args.username,
        password=args.password,
        first_name="",
        last_name="",
    )
    UserProfile.objects.create(
        user=user,
        role="manager",
        name=args.name,
    )
    print(f"created manager: {args.username}")


if __name__ == "__main__":
    main()
