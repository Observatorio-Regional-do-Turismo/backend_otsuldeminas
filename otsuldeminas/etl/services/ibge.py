from __future__ import annotations
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode
import requests
from website_backend.models import Cidade, CidadeData


IBGE_API_URL = "https://servicodados.ibge.gov.br/api/v3/agregados"

INDICATORS = {
    "populacao": {"aggregate": 4714, "variable": 93},
    "pib": {"aggregate": 5938, "variable": 37},
    "pib_per_capta": {"aggregate": 5938, "variable": 38},
    "area_territorial": {"aggregate": 1301, "variable": 615},
    "area": {"aggregate": 1301, "variable": 615},
    "densidade_demografica": {"aggregate": 1298, "variable": 29},
    "densidade": {"aggregate": 1298, "variable": 29},
    "taxa_escolarizacao": {"aggregate": 1388, "variable": 1000062},
    "escolarizacao": {"aggregate": 1388, "variable": 1000062},
    "hospedagens": {"aggregate": 6589, "variable": 1321, "classificacao": "12762[117549]"},
    "restaurantes": {"aggregate": 9528, "variable": 706, "classificacao": "12762[117550]"},
    "leitos": {"aggregate": 6589, "variable": 1321, "classificacao": "12762[117549]"},
    "munic": {"aggregate": 1329, "variable": 1000093},
    "indicador_cultural_munic": {"aggregate": 1329, "variable": 1000093},
    "munic_cultura": {"aggregate": 1329, "variable": 1000093},
    "pnad": {"aggregate": 4092, "variable": 1635},
    "estatistica_pnad": {"aggregate": 4092, "variable": 1635},
    "pnad_rendimento": {"aggregate": 4093, "variable": 4090},
    "pnad_ocupacao": {"aggregate": 4093, "variable": 4090},
    # IDH / IDHM não estão presentes na API do IBGE Agregados
    "idh": None,
    "idhm": None,
}


def _build_url(indicator: dict[str, Any], ibge_code: str) -> str:
	url = f"{IBGE_API_URL}/{indicator['aggregate']}/periodos/-1/variaveis/{indicator['variable']}"
	params = {"localidades": f"N6[{ibge_code}]"}
	if "classificacao" in indicator:
		params["classificacao"] = indicator["classificacao"]
	return f"{url}?{urlencode(params)}"


def extract_positive_integer(payload: Any) -> int:
	try:
		series = payload[0]["resultados"][0]["series"][0]["serie"]
		years = [year for year in series if str(year).isdigit()]
		latest_year = max(years, key=int)
		return int(series[latest_year])
	except (IndexError, KeyError, TypeError, ValueError) as exc:
		raise ValueError("Invalid IBGE payload: latest numeric value not found") from exc


def collect_city_indicators(cidade: Cidade, *, request_get: Callable[..., requests.Response] = requests.get, value_extractor: Callable[[Any], int] = extract_positive_integer,) -> None:
	if not cidade.ibge_code:
		return

	cidade_data, _ = CidadeData.objects.get_or_create(cidade=cidade)
	values = {}
	for field_name, indicator in INDICATORS.items():
		if indicator is None:
			continue
		try:
			response = request_get(_build_url(indicator, cidade.ibge_code), timeout=30)
			response.raise_for_status()
			value = value_extractor(response.json())
			if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
				raise ValueError(f"IBGE value for {field_name} must be a positive integer")
			values[field_name] = value
		except (Exception) as exc:
			print(f"Unable to extract values of {field_name} for {cidade.name}")

	if values:
		for field_name, value in values.items():
			setattr(cidade_data, field_name, value)
		cidade_data.save(update_fields=values.keys())
