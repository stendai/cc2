"""
Utils - Formatowanie liczb, dat, walut
Punkt 4: Podstawowe narzędzia formatowania
"""

from datetime import datetime, date
from typing import Union, Optional

def format_currency_usd(amount: Union[float, int], show_symbol: bool = True) -> str:
    """
    Formatowanie kwot w USD
    
    Args:
        amount: Kwota do sformatowania
        show_symbol: Czy pokazywać symbol $
    
    Returns:
        str: Sformatowana kwota np. "$1,234.56" lub "1,234.56"
    """
    if amount is None:
        return "N/A"
    
    try:
        if show_symbol:
            return f"${amount:,.2f}"
        else:
            return f"{amount:,.2f}"
    except (ValueError, TypeError):
        return "N/A"

def format_currency_pln(amount: Union[float, int], show_symbol: bool = True) -> str:
    """
    Formatowanie kwot w PLN
    
    Args:
        amount: Kwota do sformatowania  
        show_symbol: Czy pokazywać symbol zł
    
    Returns:
        str: Sformatowana kwota np. "1,234.56 zł" lub "1,234.56"
    """
    if amount is None:
        return "N/A"
    
    try:
        if show_symbol:
            return f"{amount:,.2f} zł"
        else:
            return f"{amount:,.2f}"
    except (ValueError, TypeError):
        return "N/A"

def format_percentage(value: Union[float, int], decimals: int = 2) -> str:
    """
    Formatowanie procentów
    
    Args:
        value: Wartość do sformatowania (np. 0.05 dla 5%)
        decimals: Liczba miejsc po przecinku
    
    Returns:
        str: Sformatowany procent np. "5.00%"
    """
    if value is None:
        return "N/A"
    
    try:
        return f"{value * 100:.{decimals}f}%"
    except (ValueError, TypeError):
        return "N/A"

def format_date(date_value: Union[datetime, date, str], format_str: str = "%Y-%m-%d") -> str:
    """
    Formatowanie dat
    
    Args:
        date_value: Data do sformatowania
        format_str: Format daty
    
    Returns:
        str: Sformatowana data
    """
    if date_value is None:
        return "N/A"
    
    try:
        if isinstance(date_value, str):
            # Spróbuj sparsować string do daty
            date_value = datetime.strptime(date_value, "%Y-%m-%d").date()
        
        if isinstance(date_value, datetime):
            return date_value.strftime(format_str)
        elif isinstance(date_value, date):
            return date_value.strftime(format_str)
        else:
            return str(date_value)
            
    except (ValueError, TypeError):
        return str(date_value) if date_value else "N/A"

def format_number(value: Union[float, int], decimals: int = 0) -> str:
    """
    Formatowanie liczb z separatorami tysięcy
    
    Args:
        value: Liczba do sformatowania
        decimals: Liczba miejsc po przecinku
    
    Returns:
        str: Sformatowana liczba np. "1,234" lub "1,234.56"
    """
    if value is None:
        return "N/A"
    
    try:
        if decimals == 0:
            return f"{int(value):,}"
        else:
            return f"{value:,.{decimals}f}"
    except (ValueError, TypeError):
        return "N/A"

def format_fx_rate(rate: Union[float, int], decimals: int = 4) -> str:
    """
    Formatowanie kursów walut
    
    Args:
        rate: Kurs do sformatowania
        decimals: Liczba miejsc po przecinku (domyślnie 4)
    
    Returns:
        str: Sformatowany kurs np. "4.2350"
    """
    if rate is None:
        return "N/A"
    
    try:
        return f"{rate:.{decimals}f}"
    except (ValueError, TypeError):
        return "N/A"

# Test funkcji formatowania
if __name__ == "__main__":
    print("Test formatowania:")
    print(f"USD: {format_currency_usd(1234.56)}")
    print(f"PLN: {format_currency_pln(5234.78)}")
    print(f"Procent: {format_percentage(0.0523)}")
    print(f"Data: {format_date(datetime.now())}")
    print(f"Liczba: {format_number(1234567.89, 2)}")
    print(f"Kurs: {format_fx_rate(4.2347)}")