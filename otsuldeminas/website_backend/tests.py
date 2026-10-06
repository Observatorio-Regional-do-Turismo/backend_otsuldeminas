from unittest.mock import Mock, patch

from django.test import TestCase
from rest_framework.test import APIClient

from etl.services.ibge import collect_city_indicators
from .models import Cidade, CidadeData, Estado


class CidadeDataTests(TestCase):
    def setUp(self):
        self.estado = Estado.objects.create(
            name="Minas Gerais",
            slug="minas-gerais",
            abbreviation="MG",
        )
        self.cidade = Cidade.objects.create(
            name="Pocos de Caldas",
            slug="pocos-de-caldas",
            ibge_code="3151800",
            state=self.estado,
        )

    @patch("etl.services.ibge.INDICATORS", {"populacao": {"aggregate": 4714, "variable": 93}})
    def test_collector_creates_city_data_when_no_indicator_is_available(self):
        collect_city_indicators(
            self.cidade,
            request_get=Mock(return_value=Mock()),
            value_extractor=Mock(side_effect=ValueError("No indicator value")),
        )

        self.assertTrue(CidadeData.objects.filter(cidade=self.cidade).exists())

    def test_city_data_is_only_in_detail_response(self):
        CidadeData.objects.create(cidade=self.cidade, populacao=163742)
        client = APIClient()

        list_response = client.get("/backend/cidades/")
        detail_response = client.get(f"/backend/cidades/{self.cidade.pk}/")

        self.assertEqual(list_response.status_code, 200)
        self.assertNotIn("information", list_response.data["results"][0])
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data["information"]["populacao"], 163742)