"""
Speaker profiles with voice characteristics and casting guidance.
"""

SPEAKER_PROFILES = {
    'Lucas': {
        'role': 'Narrator',
        'availability': 'Available',
        'description': 'Erzähler',
        'voice_characteristics': '',
        'casting_guidance': ''
    },
    'Chaos': {
        'role': 'Speaker (Female)',
        'availability': 'Available',
        'description': 'Sprecherin',
        'voice_characteristics': 'Gute Tonhöhenvielfalt und Emotionalität',
        'casting_guidance': 'Gut für Erwachsene sowie Kinderrollen geeignet'
    },
    'Sira': {
        'role': 'Speaker (Female)',
        'availability': 'Not Available',
        'description': 'Sprecherin',
        'voice_characteristics': 'Kann ihre Stimme nicht sehr variieren, klingt jung',
        'casting_guidance': 'Für junge Charaktere geeignet'
    },
    'Jade': {
        'role': 'Speaker (Female)',
        'availability': 'Not Available',
        'description': 'Sprecherin',
        'voice_characteristics': 'Tiefere, ältere Stimme mit guter Tonhöhenvielfalt, emotional',
        'casting_guidance': 'Gut für erwachsene und reife Charaktere'
    },
    'Belli': {
        'role': 'Speaker (Female)',
        'availability': 'Available',
        'description': 'Sprecherin',
        'voice_characteristics': '',
        'casting_guidance': ''
    },
    'Drystan': {
        'role': 'Speaker (Male)',
        'availability': 'Available',
        'description': 'Sprecher',
        'voice_characteristics': 'Junge Männerstimme',
        'casting_guidance': 'Gut für Teenager geeignet'
    },
    'Holger': {
        'role': 'Speaker (Male)',
        'availability': 'Available',
        'description': 'Sprecher',
        'voice_characteristics': 'Alte Männerstimme',
        'casting_guidance': 'Gut für ältere Zivis/Täter'
    },
    'Martin': {
        'role': 'Speaker (Male)',
        'availability': 'Available',
        'description': 'Sprecher',
        'voice_characteristics': 'Tiefe junge Stimme',
        'casting_guidance': 'Passt immer gut auf Cops'
    },
    'Marcel': {
        'role': 'Speaker (Male)',
        'availability': 'Available',
        'description': 'Sprecher',
        'voice_characteristics': 'Tief und jung, gut mit Emotionen',
        'casting_guidance': 'Passt gut auf Täter'
    },
    'Nils': {
        'role': 'Speaker (Male)',
        'availability': 'Available',
        'description': 'Sprecher',
        'voice_characteristics': 'Eher junge tiefe Stimme, nicht sehr emotional',
        'casting_guidance': 'Für ruhigere Charaktere geeignet'
    },
    'Marco': {
        'role': 'Speaker (Male)',
        'availability': 'Available',
        'description': 'Sprecher',
        'voice_characteristics': '',
        'casting_guidance': ''
    },
    'Jessica': {
        'role': 'Speaker (Female)',
        'availability': 'Available',
        'description': 'Sprecherin',
        'voice_characteristics': '',
        'casting_guidance': ''
    }
}

CASTING_INSTRUCTIONS = """
Die Zuteilung der Sprecher auf ein Skript ist deine Aufgabe und erfolgt nach Charakterpassung. 
Bitte beachte auch, ob die Sprecher im Trello auf verfügbar gesetzt sind oder nicht.

Passung: Gibt es z.B. viele ältere Zivis/Täter, ist Holger eine gute Wahl für diese. 
Sind die Zivis/Täter jugendlich, passt Drystan.
"""

def get_speaker_profile(speaker_name):
    """Get profile information for a speaker."""
    return SPEAKER_PROFILES.get(speaker_name, {
        'role': 'Speaker',
        'availability': 'Unknown',
        'description': '',
        'voice_characteristics': '',
        'casting_guidance': ''
    })

def get_available_speakers():
    """Get list of available speakers."""
    return [name for name, profile in SPEAKER_PROFILES.items() if profile['availability'] == 'Available']

def get_unavailable_speakers():
    """Get list of unavailable speakers."""
    return [name for name, profile in SPEAKER_PROFILES.items() if profile['availability'] == 'Not Available']
