from itools.web import AccessControl as AbakucAccessControl 

class AccessControl(AbakucAccessControl):   
    '''
    Permissions used through out the application.
    We have the following user types:
    Anonymous user:
      - this user can view all public content
      - they can also submit enquiries and job applications*
      * although this process requires them to validate their email
      which makes them registered!
    Guest user:
      A guest user is a user who is registered and is attached to an address,
      for which the manager has not made them a Member. This can only be done
      by the Branch Manager.
      The guest user can:
        - Add forum topics
        - Make enquiries and submit job applications without having to validate
        their email.
    Branch Member user:
      A brench member is a user, who has been manually added to be a part of a
      specific address by the Branch Manager.
      The branch member, can:
        - Add news, jobs, products
        - View/Manage enquiries
        - Plus what the guest user can do.
    Branch Manager user:
        - Manage company/address metadata
        - Manage permissions
        - Plus everything else that the branch member can do.
    Training Manager
      This is a special user, that only the Admin user can add, when
      creating the Training Programme.
      The training manager, can:
        - Manage training programme content, metadata
        - View statistics
        - Download members etc...
    '''
    #######################################################################
    # Security / Access Control
    #######################################################################
    def is_branch_manager(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is reviewer or member
        site_root = object.get_site_root()
        address = user.get_address()
        return (site_root.has_user_role(user.name, 'abakuc:branch_manager') or
                address.has_user_role(user.name, 'abakuc:branch_manager'))

    def is_branch_manager_or_member(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        # Is reviewer or member
        site_root = object.get_site_root()
        return (site_root.has_user_role(user.name, 'abakuc:branch_manager') or
                site_root.has_user_role(user.name, 'abakuc:branch_member'))

    def is_allowed_to_manage(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        site_root = object.get_site_root()
        return (site_root.has_user_role(user.name, 'abakuc:branch_manager') or
                site_root.has_user_role(user.name, 'abakuc:branch_member'))

    def is_allowed_to_edit(self, user, object):
        if not user:
            return False
        # Is global admin
        root = object.get_root()
        if root.is_admin(user, self):
            return True
        site_root = object.get_site_root()
        return (site_root.has_user_role(user.name, 'abakuc:branch_manager') or
                site_root.has_user_role(user.name, 'abakuc:branch_member') or
                site_root.has_user_role(user.name, 'abakuc:guest'))
