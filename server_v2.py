#!/usr/bin/env python3
"""
MCP Server: voyage-agent
Serveur MCP pour les outils de voyage et transport

Compatible avec Azure Voice Live API (MCP natif)

Outils:
- search_flights: Recherche de vols (Amadeus)
- book_flight: Réservation de vols
- search_hotels: Recherche d'hôtels (Amadeus)
- book_hotel: Réservation d'hôtels
- get_bus_schedule: Horaires SOTRACO

Auteur: WakaCore Team
Date: 2026-01-30
"""

import os
import json
from datetime import datetime, timezone
from flask import Flask, Response, request, jsonify
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# MCP SERVER BASE
# =============================================================================

class MCPServer:
    def __init__(self, name: str, description: str, version: str = "2.0.0"):
        self.name = name
        self.description = description
        self.version = version
        self.tools = {}
        self.app = Flask(__name__)
        self._setup_routes()
    
    def tool(self, name: str, description: str, parameters: dict):
        """Décorateur pour enregistrer un outil MCP"""
        def decorator(func):
            self.tools[name] = {
                "name": name,
                "description": description,
                "inputSchema": {
                    "type": "object",
                    "properties": parameters.get("properties", {}),
                    "required": parameters.get("required", [])
                },
                "handler": func
            }
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def _setup_routes(self):
        @self.app.route("/mcp", methods=["POST"])
        def mcp_endpoint():
            return self._handle_mcp_request()
        
        @self.app.route("/health", methods=["GET"])
        def health():
            return jsonify({
                "status": "ok",
                "server": self.name,
                "version": self.version,
                "tools_count": len(self.tools)
            })
        
        @self.app.route("/tools", methods=["GET"])
        def list_tools():
            tools_list = [{"name": t["name"], "description": t["description"]} for t in self.tools.values()]
            return jsonify({"tools": tools_list, "count": len(tools_list)})
        
        @self.app.route("/", methods=["GET"])
        def index():
            return jsonify({
                "name": self.name,
                "description": self.description,
                "version": self.version,
                "endpoints": {
                    "mcp": "/mcp (POST)",
                    "health": "/health",
                    "tools": "/tools"
                },
                "tools_count": len(self.tools)
            })
    
    def _handle_mcp_request(self):
        data = request.get_json()
        if not data:
            return jsonify({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}), 400
        
        request_id = data.get("id")
        method = data.get("method", "")
        params = data.get("params", {})
        
        if method == "initialize":
            return jsonify({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": self.name, "version": self.version},
                    "capabilities": {"tools": {"listChanged": False}}
                }
            })
        
        elif method == "tools/list":
            tools_list = [{
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["inputSchema"]
            } for t in self.tools.values()]
            return jsonify({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": tools_list}
            })
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name not in self.tools:
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
                })
            
            try:
                result = self.tools[tool_name]["handler"](**arguments)
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}]
                    }
                })
            except Exception as e:
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32603, "message": str(e)}
                })
        
        else:
            return jsonify({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            })
    
    def run(self, host="0.0.0.0", port=8000):
        self.app.run(host=host, port=port, threaded=True)


# =============================================================================
# CRÉATION DU SERVEUR
# =============================================================================

server = MCPServer(
    name="voyage-agent",
    description="Agent de voyage - Recherche et réservation de vols, hôtels et transport",
    version="2.0.0"
)

# Import des modules tools
from tools import tool_flight_search, tool_flight_booking
from tools import tool_hotel_search, tool_hotel_booking
from tools import tool_bus_schedule


# =============================================================================
# RECHERCHE DE VOLS
# =============================================================================

@server.tool(
    name="search_flights",
    description="""Recherche des vols disponibles avec prix et horaires via Amadeus API.

CODES AÉROPORTS (IATA - 3 lettres):
Afrique: OUA (Ouagadougou), ABJ (Abidjan), DKR (Dakar), LOS (Lagos)
Europe: CDG (Paris), LHR (Londres), FRA (Francfort)

Retourne liste des vols disponibles avec prix et détails.""",
    parameters={
        "properties": {
            "origin": {"type": "string", "description": "Code IATA de l'aéroport de départ (ex: 'OUA')"},
            "destination": {"type": "string", "description": "Code IATA de l'aéroport d'arrivée (ex: 'CDG')"},
            "departure_date": {"type": "string", "description": "Date de départ (YYYY-MM-DD)"},
            "return_date": {"type": "string", "description": "Date de retour optionnelle (YYYY-MM-DD)"},
            "adults": {"type": "integer", "description": "Nombre de passagers adultes (1-9)"},
            "travel_class": {"type": "string", "description": "Classe de voyage (ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST)"},
            "max_results": {"type": "integer", "description": "Nombre maximum de résultats (1-10)"}
        },
        "required": ["origin", "destination", "departure_date"]
    }
)
def search_flights(origin: str, destination: str, departure_date: str, return_date: str = None, adults: int = 1, travel_class: str = "ECONOMY", max_results: int = 5):
    return tool_flight_search.search_flights(
        origin=origin, destination=destination, departure_date=departure_date,
        return_date=return_date, adults=adults, travel_class=travel_class, max_results=max_results
    )


# =============================================================================
# RÉSERVATION DE VOLS
# =============================================================================

@server.tool(
    name="book_flight",
    description="""Génère un lien de réservation pour un vol sélectionné via search_flights.

PROCESSUS EN 2 ÉTAPES:
1. D'abord utilise search_flights pour obtenir les offres
2. Ensuite utilise book_flight avec l'ID de l'offre

Retourne lien de réservation et détails.""",
    parameters={
        "properties": {
            "flight_offer_id": {"type": "string", "description": "ID de l'offre de vol (fourni par search_flights)"},
            "passenger_first_name": {"type": "string", "description": "Prénom du passager"},
            "passenger_last_name": {"type": "string", "description": "Nom de famille"},
            "passenger_email": {"type": "string", "description": "Email du passager"},
            "passenger_phone": {"type": "string", "description": "Téléphone (format +226...)"},
            "passenger_date_of_birth": {"type": "string", "description": "Date de naissance (YYYY-MM-DD)"},
            "passenger_gender": {"type": "string", "description": "Genre (MALE ou FEMALE)"},
            "passenger_document_number": {"type": "string", "description": "Numéro de passeport (optionnel)"}
        },
        "required": ["flight_offer_id", "passenger_first_name", "passenger_last_name", "passenger_email", "passenger_phone", "passenger_date_of_birth"]
    }
)
def book_flight(flight_offer_id: str, passenger_first_name: str, passenger_last_name: str, passenger_email: str, passenger_phone: str, passenger_date_of_birth: str, passenger_gender: str = "MALE", passenger_document_number: str = None):
    return tool_flight_booking.book_flight(
        flight_offer_id=flight_offer_id,
        passenger={
            "first_name": passenger_first_name,
            "last_name": passenger_last_name,
            "email": passenger_email,
            "phone": passenger_phone,
            "date_of_birth": passenger_date_of_birth,
            "gender": passenger_gender,
            "document_number": passenger_document_number
        }
    )


# =============================================================================
# RECHERCHE D'HÔTELS
# =============================================================================

@server.tool(
    name="search_hotels",
    description="""Recherche des hôtels disponibles avec prix via Amadeus API.

CODES DE VILLES (IATA):
Afrique: OUA (Ouagadougou), ABJ (Abidjan), DKR (Dakar)
Europe: PAR (Paris), LON (Londres), MAD (Madrid)

Retourne liste des hôtels disponibles avec prix.""",
    parameters={
        "properties": {
            "city_code": {"type": "string", "description": "Code IATA de la ville (ex: 'OUA', 'PAR')"},
            "check_in_date": {"type": "string", "description": "Date d'arrivée (YYYY-MM-DD)"},
            "check_out_date": {"type": "string", "description": "Date de départ (YYYY-MM-DD)"},
            "adults": {"type": "integer", "description": "Nombre d'adultes par chambre"},
            "rooms": {"type": "integer", "description": "Nombre de chambres souhaitées"},
            "hotel_name": {"type": "string", "description": "Nom d'hôtel spécifique (optionnel)"},
            "max_results": {"type": "integer", "description": "Nombre maximum de résultats"}
        },
        "required": ["city_code", "check_in_date", "check_out_date"]
    }
)
def search_hotels(city_code: str, check_in_date: str, check_out_date: str, adults: int = 1, rooms: int = 1, hotel_name: str = None, max_results: int = 5):
    return tool_hotel_search.search_hotels(
        city_code=city_code, check_in_date=check_in_date, check_out_date=check_out_date,
        adults=adults, rooms=rooms, hotel_name=hotel_name, max_results=max_results
    )


# =============================================================================
# RÉSERVATION D'HÔTELS
# =============================================================================

@server.tool(
    name="book_hotel",
    description="""Génère un lien de réservation pour un hôtel sélectionné.

PROCESSUS EN 2 ÉTAPES:
1. D'abord utilise search_hotels pour obtenir les offres
2. Ensuite utilise book_hotel avec l'ID de l'offre

Retourne lien de réservation et détails.""",
    parameters={
        "properties": {
            "hotel_offer_id": {"type": "string", "description": "ID de l'offre d'hôtel (fourni par search_hotels)"},
            "guest_first_name": {"type": "string", "description": "Prénom du client"},
            "guest_last_name": {"type": "string", "description": "Nom de famille"},
            "guest_email": {"type": "string", "description": "Email du client"},
            "guest_phone": {"type": "string", "description": "Téléphone (format +226...)"},
            "card_type": {"type": "string", "description": "Type de carte (VISA, MASTERCARD)"},
            "card_number": {"type": "string", "description": "Numéro de carte (optionnel)"}
        },
        "required": ["hotel_offer_id", "guest_first_name", "guest_last_name", "guest_email", "guest_phone"]
    }
)
def book_hotel(hotel_offer_id: str, guest_first_name: str, guest_last_name: str, guest_email: str, guest_phone: str, card_type: str = "VISA", card_number: str = None):
    return tool_hotel_booking.book_hotel(
        hotel_offer_id=hotel_offer_id,
        guest={
            "first_name": guest_first_name,
            "last_name": guest_last_name,
            "email": guest_email,
            "phone": guest_phone
        },
        payment={
            "card_type": card_type,
            "card_number": card_number
        }
    )


# =============================================================================
# TRANSPORT LOCAL
# =============================================================================

@server.tool(
    name="get_bus_schedule",
    description="""Horaires des bus SOTRACO (Ouagadougou) et lignes inter-urbaines.

LIGNES URBAINES SOTRACO:
1: Gare Routière ↔ Ouaga 2000
2: Zone du Bois ↔ Patte d'Oie
3: Aéroport ↔ Université
4: Tampouy ↔ Gounghin
5: Pissy ↔ CHU Yalgado

LIGNES INTERURBAINES: Ouagadougou ↔ Bobo-Dioulasso, Koudougou""",
    parameters={
        "properties": {
            "line_number": {"type": "string", "description": "Numéro de ligne SOTRACO (1-5) pour les bus urbains"},
            "from_city": {"type": "string", "description": "Ville de départ pour les trajets interurbains"},
            "to_city": {"type": "string", "description": "Ville d'arrivée pour les trajets interurbains"}
        },
        "required": []
    }
)
def get_bus_schedule(line_number: str = None, from_city: str = None, to_city: str = None):
    return tool_bus_schedule.execute({"line_number": line_number, "from_city": from_city, "to_city": to_city})


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    print("🛫 Démarrage du serveur MCP voyage-agent v2.0.0...")
    server.run(host="0.0.0.0", port=8000)
