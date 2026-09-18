from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

import requests

from website_backend.models import Cidade


IBGE_API_URL = "https://servicodados.ibge.gov.br/api/v3/agregados"

INDICATORS = {
	"pib": {"aggregate": 5938, "variable": 37},
	"populacao": {"aggregate": 4714, "variable": 93},
	"hospedagens": {"aggregate": 6589, "variable": 1321},
	"restaurantes": {
		"aggregate": 9528,
		"variable": 706,
		"classificacao": "12762[117550]",
	},
}


def _build_url(indicator: dict[str, Any], ibge_code: str) -> str:
	url = (
		f"{IBGE_API_URL}/{indicator['aggregate']}/periodos/-1/"
		f"variaveis/{indicator['variable']}"
	)
	params = {"localidades": f"N6[{ibge_code}]"}
	if "classificacao" in indicator:
		params["classificacao"] = indicator["classificacao"]
	return f"{url}?{urlencode(params)}"


def extract_positive_integer(payload: Any) -> int:
	"""Extract the value from the latest year in an IBGE response."""
	try:
		series = payload[0]["resultados"][0]["series"][0]["serie"]
		years = [year for year in series if str(year).isdigit()]
		latest_year = max(years, key=int)
		return int(series[latest_year])
	except (IndexError, KeyError, TypeError, ValueError) as exc:
		raise ValueError("Invalid IBGE payload: latest numeric value not found") from exc


def collect_city_indicators(
	cidade: Cidade,
	*,
	request_get: Callable[..., requests.Response] = requests.get,
	value_extractor: Callable[[Any], int] = extract_positive_integer,
) -> None:
	if not cidade.ibge_code:
		return

	values = {}
	for field_name, indicator in INDICATORS.items():
		response = request_get(_build_url(indicator, cidade.ibge_code), timeout=30)
		response.raise_for_status()
		value = value_extractor(response.json())
		if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
			raise ValueError(f"IBGE value for {field_name} must be a positive integer")
		values[field_name] = value

	Cidade.objects.filter(pk=cidade.pk).update(**values)
