"""Reusable calendar helpers for Giro de Supervisores - Nelson Casella."""
from calendar import monthrange
from datetime import date

SPANISH = ['LUNES','MARTES','MIÉRCOLES','JUEVES','VIERNES','SÁBADO','DOMINGO']

def month_days(year, month):
    return monthrange(year, month)[1]

def calendar_matrix(year, month):
    first, days = monthrange(year, month)
    rows=[]; week=[None]*first
    for d in range(1, days+1):
        week.append(d)
        if len(week)==7:
            rows.append(week); week=[]
    if week: rows.append(week+[None]*(7-len(week)))
    return rows

def day_state(day, licenses, unavailable, holidays):
    if day in holidays: return 'FERIADO'
    if day in licenses: return 'LICENCIA'
    if day in unavailable: return 'NO DISPONIBLE'
    return 'DISPONIBLE'
