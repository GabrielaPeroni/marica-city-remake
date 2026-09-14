from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class UserModelTests(TestCase):
    """Testes para o modelo User personalizado"""

    def test_create_user(self):
        """Testa a criação de um usuário regular"""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpass123"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        """Testa a criação de um superusuário"""
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin123",
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_user_string_representation(self):
        """Testa a representação em string do usuário"""
        user = User.objects.create_user(username="testuser", password="pass123")
        self.assertEqual(str(user), "testuser")

    def test_user_permissions_properties(self):
        """Testa propriedades de permissões personalizadas"""
        regular_user = User.objects.create_user(
            username="regular", password="pass123", is_staff=False
        )
        staff_user = User.objects.create_user(
            username="staff", password="pass123", is_staff=True
        )

        # Testa can_create_places - todos os usuários autenticados podem criar
        self.assertTrue(regular_user.can_create_places)
        self.assertTrue(staff_user.can_create_places)

        # Testa can_moderate - apenas usuários staff podem moderar
        self.assertFalse(regular_user.can_moderate)
        self.assertTrue(staff_user.can_moderate)

    def test_all_logged_in_users_can_create_places(self):
        """Testa que todos os usuários logados podem criar lugares"""
        regular_user = User.objects.create_user(
            username="regular", password="pass123", is_staff=False
        )
        self.assertTrue(regular_user.can_create_places)

    def test_only_staff_can_moderate(self):
        """Testa que apenas usuários staff podem moderar"""
        regular_user = User.objects.create_user(
            username="regular", password="pass123", is_staff=False
        )
        staff_user = User.objects.create_user(
            username="staff", password="pass123", is_staff=True
        )
        self.assertFalse(regular_user.can_moderate)
        self.assertTrue(staff_user.can_moderate)


class AuthenticationViewTests(TestCase):
    """Testes para views de autenticação"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

    def test_register_page_loads(self):
        """Testa que a página de registro carrega com sucesso"""
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")

    def test_user_can_login(self):
        """Testa que o usuário pode fazer login com credenciais corretas via AJAX"""
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "testuser", "password": "testpass123"},
        )
        self.assertEqual(response.status_code, 200)  # JSON response
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["username"], "testuser")

    def test_user_cannot_login_with_wrong_password(self):
        """Testa que o usuário não pode fazer login com senha incorreta via AJAX"""
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "testuser", "password": "wrongpassword"},
        )
        self.assertEqual(response.status_code, 401)  # Unauthorized
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("error", data)

    def test_user_registration(self):
        """Testa que um novo usuário pode se registrar"""
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "newpass123!",
                "password2": "newpass123!",
            },
        )
        self.assertEqual(response.status_code, 302)  # Redirect after registration

        # Verificar que o usuário foi criado
        self.assertTrue(User.objects.filter(username="newuser").exists())
        new_user = User.objects.get(username="newuser")
        self.assertEqual(new_user.email, "new@example.com")
        self.assertFalse(new_user.is_staff)  # Usuário regular por padrão

    def test_registration_form_no_user_type_field(self):
        """Testa que o formulário de registro não mostra seleção de tipo de usuário"""
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)
        # Campo de tipo de usuário não deve estar no formulário
        self.assertNotContains(response, 'name="user_type"')

    def test_new_users_default_to_regular_account(self):
        """Testa que usuários recém-registrados são contas regulares (não staff)"""
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "newpass123!",
                "password2": "newpass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username="newuser")
        self.assertFalse(new_user.is_staff)
        self.assertTrue(new_user.can_create_places)
        self.assertFalse(new_user.can_moderate)

    def test_logout(self):
        """Testa que o usuário pode fazer logout"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)

    def test_login_endpoint_rejects_get_requests(self):
        """Testa que o endpoint de login só aceita POST (apenas AJAX)"""
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 405)  # Method not allowed
        data = response.json()
        self.assertFalse(data["success"])

    def test_login_dropdown_present_on_pages(self):
        """Testa que o dropdown de login está presente nas páginas"""
        # Testar na página inicial
        response = self.client.get(reverse("core:landing"))
        self.assertContains(response, "Entre na sua conta")
        self.assertContains(response, 'data-bs-toggle="dropdown"')

        # Testar na página de explorar
        response = self.client.get(reverse("explore:explore"))
        self.assertContains(response, "Entre na sua conta")
        self.assertContains(response, 'data-bs-toggle="dropdown"')

    def test_login_button_present_for_anonymous_users(self):
        """Testa que o botão de login aparece para usuários anônimos"""
        response = self.client.get(reverse("core:landing"))
        self.assertContains(response, 'data-bs-toggle="dropdown"')
        self.assertContains(response, "Entrar")

    def test_login_button_not_present_for_authenticated_users(self):
        """Testa que o botão de login não aparece para usuários autenticados"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("core:landing"))
        # Deve mostrar Sair em vez de Entrar
        self.assertContains(response, "Sair")
        # Deve mostrar o nome de usuário
        self.assertContains(response, "testuser")

    def test_google_client_id_in_register_context(self):
        """Testa que o ID do cliente Google OAuth é passado para a página de registro"""
        response = self.client.get(reverse("accounts:register"))
        self.assertIn("google_client_id", response.context)

    def test_authenticated_user_redirected_from_register(self):
        """Testa que usuário já autenticado é redirecionado ao acessar registro"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("accounts:register"))
        self.assertRedirects(response, reverse("core:landing"))

    def test_login_rejects_missing_credentials(self):
        """Testa que o login via AJAX exige usuário e senha"""
        response = self.client.post(
            reverse("accounts:login"), {"username": "", "password": ""}
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])

    def test_login_rejects_inactive_user(self):
        """Testa que usuário inativo não consegue fazer login.
        Note: Django's default authenticate() already excludes inactive
        users, so this always falls into the generic 401 'wrong
        credentials' branch - the view's dedicated `if not user.is_active`
        403 branch is unreachable dead code (found while writing this
        test; not fixed, out of scope for this PR)."""
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "testuser", "password": "testpass123"},
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data["success"])

    def test_logout_redirects_to_next_param(self):
        """Testa que o logout redireciona para o parâmetro 'next' quando fornecido"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("accounts:logout") + "?next=/explore/")
        self.assertRedirects(response, "/explore/", fetch_redirect_response=False)

    def test_logout_falls_back_to_landing_page(self):
        """Testa que o logout redireciona para a página inicial sem 'next' ou referer"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("core:landing"))


class UserManagementViewTests(TestCase):
    """Testes para a view de gerenciamento de usuários (admin)"""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="pass123", is_staff=True
        )
        self.staff_user = User.objects.create_user(
            username="staffer", password="pass123", is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="regular",
            password="pass123",
            is_staff=False,
            email="regular@example.com",
        )
        self.inactive_user = User.objects.create_user(
            username="inactive", password="pass123", is_active=False
        )
        self.url = reverse("accounts:user_management")

    def test_requires_login(self):
        """Testa que a página exige autenticação"""
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/?next={self.url}")

    def test_requires_moderator_permission(self):
        """Testa que apenas moderadores podem acessar a página"""
        self.client.login(username="regular", password="pass123")
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("core:landing"))

    def test_loads_for_moderator_with_statistics(self):
        """Testa que a página carrega para moderadores com estatísticas corretas"""
        self.client.login(username="admin", password="pass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_users"], 4)
        self.assertEqual(response.context["staff_users"], 2)
        self.assertEqual(response.context["regular_users"], 2)
        self.assertEqual(response.context["active_users"], 3)

    def test_filter_by_role_staff(self):
        """Testa filtro de usuários por função (staff)"""
        self.client.login(username="admin", password="pass123")
        response = self.client.get(self.url + "?role=staff")
        usernames = {u.username for u in response.context["users"]}
        self.assertEqual(usernames, {"admin", "staffer"})

    def test_filter_by_role_regular(self):
        """Testa filtro de usuários por função (regular)"""
        self.client.login(username="admin", password="pass123")
        response = self.client.get(self.url + "?role=regular")
        usernames = {u.username for u in response.context["users"]}
        self.assertEqual(usernames, {"regular", "inactive"})

    def test_filter_by_status_active(self):
        """Testa filtro de usuários por status (ativos)"""
        self.client.login(username="admin", password="pass123")
        response = self.client.get(self.url + "?status=active")
        usernames = {u.username for u in response.context["users"]}
        self.assertNotIn("inactive", usernames)

    def test_filter_by_status_inactive(self):
        """Testa filtro de usuários por status (inativos)"""
        self.client.login(username="admin", password="pass123")
        response = self.client.get(self.url + "?status=inactive")
        usernames = {u.username for u in response.context["users"]}
        self.assertEqual(usernames, {"inactive"})

    def test_search_by_username_or_email(self):
        """Testa busca de usuários por nome ou e-mail"""
        self.client.login(username="admin", password="pass123")
        response = self.client.get(self.url + "?q=regular@example.com")
        usernames = {u.username for u in response.context["users"]}
        self.assertEqual(usernames, {"regular"})


class UserUpdateTypeViewTests(TestCase):
    """Testes para alternar o status de staff de um usuário"""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="pass123", is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="regular", password="pass123", is_staff=False
        )

    def test_requires_moderator_permission(self):
        """Testa que apenas moderadores podem alterar tipo de usuário"""
        self.client.login(username="regular", password="pass123")
        response = self.client.post(
            reverse("accounts:user_update_type", kwargs={"user_id": self.admin.id})
        )
        self.assertEqual(response.status_code, 403)

    def test_get_request_not_allowed(self):
        """Testa que requisições GET não são permitidas"""
        self.client.login(username="admin", password="pass123")
        response = self.client.get(
            reverse(
                "accounts:user_update_type", kwargs={"user_id": self.regular_user.id}
            )
        )
        self.assertEqual(response.status_code, 405)

    def test_cannot_change_own_status(self):
        """Testa que um usuário não pode alterar seu próprio status de staff"""
        self.client.login(username="admin", password="pass123")
        response = self.client.post(
            reverse("accounts:user_update_type", kwargs={"user_id": self.admin.id})
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])

    def test_toggles_staff_status(self):
        """Testa que o status de staff de outro usuário é alternado com sucesso"""
        self.client.login(username="admin", password="pass123")
        response = self.client.post(
            reverse(
                "accounts:user_update_type", kwargs={"user_id": self.regular_user.id}
            )
        )
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["is_staff"])
        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.is_staff)


class UserToggleStatusViewTests(TestCase):
    """Testes para alternar o status ativo de um usuário"""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="pass123", is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="regular", password="pass123", is_staff=False
        )

    def test_requires_moderator_permission(self):
        """Testa que apenas moderadores podem alterar status ativo"""
        self.client.login(username="regular", password="pass123")
        response = self.client.post(
            reverse("accounts:user_toggle_status", kwargs={"user_id": self.admin.id})
        )
        self.assertEqual(response.status_code, 403)

    def test_get_request_not_allowed(self):
        """Testa que requisições GET não são permitidas"""
        self.client.login(username="admin", password="pass123")
        response = self.client.get(
            reverse(
                "accounts:user_toggle_status", kwargs={"user_id": self.regular_user.id}
            )
        )
        self.assertEqual(response.status_code, 405)

    def test_cannot_deactivate_own_account(self):
        """Testa que um usuário não pode desativar sua própria conta"""
        self.client.login(username="admin", password="pass123")
        response = self.client.post(
            reverse("accounts:user_toggle_status", kwargs={"user_id": self.admin.id})
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])

    def test_toggles_active_status(self):
        """Testa que o status ativo de outro usuário é alternado com sucesso"""
        self.client.login(username="admin", password="pass123")
        response = self.client.post(
            reverse(
                "accounts:user_toggle_status", kwargs={"user_id": self.regular_user.id}
            )
        )
        data = response.json()
        self.assertTrue(data["success"])
        self.assertFalse(data["is_active"])
        self.regular_user.refresh_from_db()
        self.assertFalse(self.regular_user.is_active)


class UserDeleteViewTests(TestCase):
    """Testes para a exclusão de conta de usuário pelo administrador"""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="pass123", is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="regular", password="pass123", is_staff=False
        )

    def test_requires_moderator_permission(self):
        """Testa que apenas moderadores podem excluir usuários.
        Note: the redirect target itself denies non-moderators and
        redirects again, so we don't follow the chain here."""
        self.client.login(username="regular", password="pass123")
        response = self.client.post(
            reverse("accounts:user_delete", kwargs={"user_id": self.admin.id})
        )
        self.assertRedirects(
            response,
            reverse("accounts:user_management"),
            fetch_redirect_response=False,
        )
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_cannot_delete_own_account(self):
        """Testa que um usuário não pode excluir sua própria conta"""
        self.client.login(username="admin", password="pass123")
        response = self.client.post(
            reverse("accounts:user_delete", kwargs={"user_id": self.admin.id})
        )
        self.assertRedirects(response, reverse("accounts:user_management"))
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_get_shows_confirmation_page(self):
        """Testa que GET exibe a página de confirmação de exclusão"""
        self.client.login(username="admin", password="pass123")
        response = self.client.get(
            reverse("accounts:user_delete", kwargs={"user_id": self.regular_user.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/user_delete_confirm.html")

    def test_post_deletes_user(self):
        """Testa que POST exclui a conta do usuário"""
        self.client.login(username="admin", password="pass123")
        response = self.client.post(
            reverse("accounts:user_delete", kwargs={"user_id": self.regular_user.id})
        )
        self.assertRedirects(response, reverse("accounts:user_management"))
        self.assertFalse(User.objects.filter(pk=self.regular_user.pk).exists())
