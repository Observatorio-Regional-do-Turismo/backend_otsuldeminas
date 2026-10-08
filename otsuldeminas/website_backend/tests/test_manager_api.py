from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from website_backend.models import Cidade, Estado, GestorCidade, GestorIGR, IGR, Noticia
from website_backend.serializers import CidadeSerializer, IGRSerializer, NoticiaSerializer


class ManagerApiTests(TestCase):
  def setUp(self):
    self.state = Estado.objects.create(name="Minas Gerais", slug="minas-gerais", abbreviation="MG")
    self.igr = IGR.objects.create(name="Circuito das Águas", slug="circuito-das-aguas")
    self.city = Cidade.objects.create(
      name="Caxambu",
      slug="caxambu",
      state=self.state,
      igr=self.igr,
    )
    self.other_city = Cidade.objects.create(
      name="Poços de Caldas",
      slug="pocos-de-caldas",
      state=self.state,
    )
    user_model = get_user_model()
    self.city_manager = user_model.objects.create_user(
      username="city-manager",
      password="A-different-and-strong-password-583!",
    )
    GestorCidade.objects.create(user=self.city_manager, cidade=self.city)
    self.igr_manager = user_model.objects.create_user(
      username="igr-manager",
      password="Another-different-and-strong-password-638!",
    )
    GestorIGR.objects.create(user=self.igr_manager, igr=self.igr)
    self.client = APIClient()

  def test_manager_api_rejects_anonymous_requests(self):
    response = self.client.get("/backend/gestao/cidades/")

    self.assertIn(response.status_code, (401, 403))

  def test_city_manager_only_sees_assigned_city_and_news(self):
    own_news = Noticia.objects.create(
      title="Notícia da cidade",
      slug="noticia-da-cidade",
      cidade=self.city,
    )
    foreign_news = Noticia.objects.create(
      title="Notícia externa",
      slug="noticia-externa",
      cidade=self.other_city,
    )
    self.client.force_authenticate(self.city_manager)

    city_response = self.client.get("/backend/gestao/cidades/")
    foreign_city_response = self.client.get(f"/backend/gestao/cidades/{self.other_city.pk}/")
    news_response = self.client.get("/backend/gestao/noticias/")

    self.assertEqual(city_response.data["count"], 1)
    self.assertEqual(city_response.data["results"][0]["id"], self.city.pk)
    self.assertEqual(foreign_city_response.status_code, 404)
    news_ids = {item["id"] for item in news_response.data["results"]}
    self.assertEqual(news_ids, {own_news.pk})
    self.assertNotIn(foreign_news.pk, news_ids)

  def test_city_manager_cannot_create_news_for_another_city(self):
    self.client.force_authenticate(self.city_manager)

    response = self.client.post(
      "/backend/gestao/noticias/",
      {
        "title": "Tentativa de acesso cruzado",
        "slug": "tentativa-acesso-cruzado",
        "cidade": self.other_city.pk,
        "published_at": "2026-10-08T16:00:00-03:00",
      },
      format="json",
    )

    self.assertEqual(response.status_code, 400)
    self.assertFalse(Noticia.objects.filter(slug="tentativa-acesso-cruzado").exists())

  def test_igr_manager_can_only_edit_igr_news_and_rich_text_is_sanitized(self):
    self.client.force_authenticate(self.igr_manager)

    response = self.client.post(
      "/backend/gestao/noticias/",
      {
        "title": "Notícia da IGR",
        "slug": "noticia-da-igr",
        "content": '<p onclick="alert(1)">Conteúdo <strong>formatado</strong></p><script>alert(1)</script>',
        "published_at": "2026-10-08T16:00:00-03:00",
      },
      format="json",
    )

    self.assertEqual(response.status_code, 201)
    noticia = Noticia.objects.get(slug="noticia-da-igr")
    self.assertEqual(noticia.igr, self.igr)
    self.assertIsNone(noticia.cidade)
    self.assertNotIn("script", noticia.content)
    self.assertNotIn("onclick", noticia.content)
    self.assertIn("<strong>", noticia.content)
    foreign_news = Noticia.objects.create(
      title="Notícia de outra cidade",
      slug="noticia-outra-cidade",
      cidade=self.other_city,
    )
    denied_update = self.client.patch(
      f"/backend/gestao/noticias/{foreign_news.pk}/",
      {"title": "Alteração não permitida"},
      format="json",
    )
    self.assertEqual(denied_update.status_code, 404)
    foreign_news.refresh_from_db()
    self.assertEqual(foreign_news.title, "Notícia de outra cidade")

  def test_public_serializers_sanitize_rich_text_before_returning_html(self):
    self.city.description = '<p onclick="alert(1)">Cidade</p><script>alert(1)</script>'
    self.city.save()
    self.igr.description = '<p>IGR</p><script>alert(1)</script>'
    self.igr.save()
    noticia = Noticia.objects.create(
      title="Conteúdo inseguro",
      slug="conteudo-inseguro",
      content='<p>Notícia</p><img src=x onerror="alert(1)">',
    )

    city_description = CidadeSerializer(self.city).data["description"]
    igr_description = IGRSerializer(self.igr).data["description"]
    news_content = NoticiaSerializer(noticia).data["content"]
    self.client.force_authenticate(self.city_manager)
    manager_city_description = self.client.get(
      f"/backend/gestao/cidades/{self.city.pk}/"
    ).data["description"]

    self.assertNotIn("onclick", city_description)
    self.assertNotIn("script", city_description)
    self.assertNotIn("script", igr_description)
    self.assertNotIn("onerror", news_content)
    self.assertNotIn("onclick", manager_city_description)
    self.assertNotIn("script", manager_city_description)

  def test_manager_login_requires_a_csrf_token_and_valid_manager(self):
    csrf_client = APIClient(enforce_csrf_checks=True)
    csrf_response = csrf_client.get("/backend/auth/csrf/")
    token = csrf_response.json()["csrfToken"]
    rejected_without_csrf = csrf_client.post(
      "/backend/auth/login/",
      {"username": "city-manager", "password": "A-different-and-strong-password-583!"},
      format="json",
    )
    response = csrf_client.post(
      "/backend/auth/login/",
      {"username": "city-manager", "password": "A-different-and-strong-password-583!"},
      format="json",
      HTTP_X_CSRFTOKEN=token,
      HTTP_ORIGIN="http://localhost:3000",
    )

    self.assertEqual(rejected_without_csrf.status_code, 403)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.json()["scopes"][0]["type"], "cidade")
    self.assertIn("sessionid", csrf_client.cookies)
    rejected_state_change = csrf_client.post(
      "/backend/gestao/noticias/",
      {
        "title": "Sem CSRF",
        "slug": "sem-csrf",
        "published_at": "2026-10-08T16:00:00-03:00",
      },
      format="json",
    )
    self.assertEqual(rejected_state_change.status_code, 403)

  def test_manager_entities_cannot_be_created_or_deleted_from_the_portal(self):
    self.client.force_authenticate(self.city_manager)

    create_response = self.client.post("/backend/gestao/cidades/", {}, format="json")
    delete_response = self.client.delete(f"/backend/gestao/cidades/{self.city.pk}/")

    self.assertEqual(create_response.status_code, 405)
    self.assertEqual(delete_response.status_code, 405)
