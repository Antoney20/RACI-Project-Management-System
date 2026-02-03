def is_admin(user):
    return user.role  == "admin"


def is_supervisor(user):
    return user.role  in  ("supervisor", "office_admin")


def is_staff(user):
    return user.role == "staff"