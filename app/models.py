from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, user_dict):
        self.user_dict = user_dict

    def get_id(self):
        return str(self.user_dict['_id'])
    
    def get_email(self):
        return self.user_dict['email']
    
    @property
    def is_active(self):
        return True
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False

    def __get__item(self, item):
        return self.user_dict[item]