from allauth.account.adapter import DefaultAccountAdapter

class MomsOnlyAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        email = None
        if request.user.is_authenticated:
            email = request.user.email
        else:
            email = request.POST.get('email') or request.GET.get('email')

        return bool(email and email.lower().endswith("@valerievv.com"))
        # return bool(email and email.lower().endswith("@momsinmotion.net"))