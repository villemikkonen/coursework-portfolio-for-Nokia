from system_user import SystemUser
from database_manager import DatabaseManager

class AccessManager:

    def __init__(self):
        pass



    # TODO: create functionality for progressing from log in."grant_access()".
    # TODO: implement password checking later.
    """    
    def check_password(self, user_id, password):
        correct_info = DatabaseManager.get_log_in()
        if correct_info == [user_id, password]:
            return True
        else:
            return False
    """

    def grant_access(self, user, required_level):
        if user.access_level >= required_level:
            return True
        else:
            return False



