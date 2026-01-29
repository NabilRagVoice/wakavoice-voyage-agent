#!/usr/bin/env python3
"""
MCP Server: voyage-agent
Serveur MCP pour les outils de voyage et transport

Outils:
- search_flights: Recherche de vols (Amadeus)
- book_flight: Réservation de vols
- search_hotels: Recherche d'hôtels (Amadeus)
- book_hotel: Réservation d'hôtels
- get_bus_schedule: Horaires SOTRACO

Auteur: WakaCore Team
Date: 2026-01-29
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ajouter le chemin parent pour importer les tools
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP

# Import des modules tools
from tools import tool_flight_search, tool_flight_booking
from tools import tool_hotel_search, tool_hotel_booking
from tools import tool_bus_schedule

# Créer le serveur MCP
mcp = FastMCP(
    "voyage-agent",
    instructions="Agent de voyage - Recherche et réservation de vols, hôtels et transport",
    host="0.0.0.0",
    port=8000
)


# =============================================================================
# OUTILS DE RECHERCHE DE VOLS
# =============================================================================

@mcp.tool()
def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str = None,
    adults: int = 1,
    travel_class: str = "ECONOMY",
    max_results: int = 5
) -> dict:
    """
    Recherche des vols disponibles avec prix et horaires via Amadeus API.
    
    CODES AÉROPORTS (IATA - 3 lettres):
    Afrique: OUA (Ouagadougou), ABJ (Abidjan), DKR (Dakar), LOS (Lagos)
    Europe: CDG (Paris), LHR (Londres), FRA (Francfort)
    
    Args:
        origin: Code IATA de l'aéroport de départ (ex: "OUA")
        destination: Code IATA de l'aéroport d'arrivée (ex: "CDG")
        departure_date: Date de départ (YYYY-MM-DD)
        return_date: Date de retour optionnelle (YYYY-MM-DD)
        adults: Nombre de passagers adultes (1-9)
        travel_class: Classe de voyage (ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST)
        max_results: Nombre maximum de résultats (1-10)
    
    Returns:
        dict: Liste des vols disponibles avec prix et détails
    """
    return tool_flight_search.search_flights(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        adults=adults,
        travel_class=travel_class,
        max_results=max_results
    )


@mcp.tool()
def book_flight(
    flight_offer_id: str,
    passenger_first_name: str,
    passenger_last_name: str,
    passenger_email: str,
    passenger_phone: str,
    passenger_date_of_birth: str,
    passenger_gender: str = "MALE",
    passenger_document_number: str = None
) -> dict:
    """
    Génère un lien de réservation pour un vol sélectionné via search_flights.
    
    PROCESSUS EN 2 ÉTAPES:
    1. D'abord utilise search_flights pour obtenir les offres
    2. Ensuite utilise book_flight avec l'ID de l'offre
    
    Args:
        flight_offer_id: ID de l'offre de vol (fourni par search_flights)
        passenger_first_name: Prénom du passager
        passenger_last_name: Nom de famille
        passenger_email: Email du passager
        passenger_phone: Téléphone (format +226...)
        passenger_date_of_birth: Date de naissance (YYYY-MM-DD)
        passenger_gender: Genre (MALE ou FEMALE)
        passenger_document_number: Numéro de passeport (optionnel)
    
    Returns:
        dict: Lien de réservation et détails
    """
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
# OUTILS DE RECHERCHE D'HÔTELS
# =============================================================================

@mcp.tool()
def search_hotels(
    city_code: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 1,
    rooms: int = 1,
    hotel_name: str = None,
    max_results: int = 5
) -> dict:
    """
    Recherche des hôtels disponibles avec prix via Amadeus API.
    
    CODES DE VILLES (IATA):
    Afrique: OUA (Ouagadougou), ABJ (Abidjan), DKR (Dakar)
    Europe: PAR (Paris), LON (Londres), MAD (Madrid)
    
    Args:
        city_code: Code IATA de la ville (ex: "OUA", "PAR")
        check_in_date: Date d'arrivée (YYYY-MM-DD)
        check_out_date: Date de départ (YYYY-MM-DD)
        adults: Nombre d'adultes par chambre
        rooms: Nombre de chambres souhaitées
        hotel_name: Nom d'hôtel spécifique (optionnel)
        max_results: Nombre maximum de résultats
    
    Returns:
        dict: Liste des hôtels disponibles avec prix
    """
    return tool_hotel_search.search_hotels(
        city_code=city_code,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        adults=adults,
        rooms=rooms,
        hotel_name=hotel_name,
        max_results=max_results
    )


@mcp.tool()
def book_hotel(
    hotel_offer_id: str,
    guest_first_name: str,
    guest_last_name: str,
    guest_email: str,
    guest_phone: str,
    card_type: str = "VISA",
    card_number: str = None
) -> dict:
    """
    Génère un lien de réservation pour un hôtel sélectionné.
    
    PROCESSUS EN 2 ÉTAPES:
    1. D'abord utilise search_hotels pour obtenir les offres
    2. Ensuite utilise book_hotel avec l'ID de l'offre
    
    Args:
        hotel_offer_id: ID de l'offre d'hôtel (fourni par search_hotels)
        guest_first_name: Prénom du client
        guest_last_name: Nom de famille
        guest_email: Email du client
        guest_phone: Téléphone (format +226...)
        card_type: Type de carte (VISA, MASTERCARD)
        card_number: Numéro de carte (optionnel, pour génération lien)
    
    Returns:
        dict: Lien de réservation et détails
    """
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
# OUTILS DE TRANSPORT LOCAL
# =============================================================================

@mcp.tool()
def get_bus_schedule(
    line_number: str = None,
    from_city: str = None,
    to_city: str = None
) -> dict:
    """
    Horaires des bus SOTRACO (Ouagadougou) et lignes inter-urbaines.
    
    LIGNES URBAINES SOTRACO:
    1: Gare Routière ↔ Ouaga 2000
    2: Zone du Bois ↔ Patte d'Oie
    3: Aéroport ↔ Université
    4: Tampouy ↔ Gounghin
    5: Pissy ↔ CHU Yalgado
    
    LIGNES INTERURBAINES:
    - Ouagadougou ↔ Bobo-Dioulasso
    - Ouagadougou ↔ Koudougou
    
    Args:
        line_number: Numéro de ligne SOTRACO (1-5) pour les bus urbains
        from_city: Ville de départ pour les trajets interurbains
        to_city: Ville d'arrivée pour les trajets interurbains
    
    Returns:
        dict: Horaires, arrêts, tarifs et fréquences
    """
    return tool_bus_schedule.execute({
        "line_number": line_number,
        "from_city": from_city,
        "to_city": to_city
    })


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    print("🛫 Démarrage du serveur MCP voyage-agent...")
    # Mode HTTP/SSE pour Container Apps
    mcp.run(transport="sse")
