class SystemUser:

    def __init__(self, user_id, name, password, access_level = 0):
        self.user_id = user_id
        self.name = name
        self.password = password
        self.access_level = access_level



    # Method for setting the access level of users'.
    def set_access_level(self, access_level):
        self.access_level = access_level
        return access_level
