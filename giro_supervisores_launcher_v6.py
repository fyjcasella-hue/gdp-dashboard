# Giro de Supervisores - Nelson Casella
# Opción 2: rotación equilibrada de zonas secundarias.
# Se conserva la lógica estable de v5 y, después de generar el mes,
# se realizan intercambios locales entre agentes ya asignados al mismo día.
# CASTRO queda completamente excluido de los intercambios.

import tkinter as tk
from giro_supervisores_launcher_v5 import GiroApp


_original_generate = GiroApp.generate


def _zone_counts_before_day(cron, day, agent):
    """Cantidad de veces que agent pasó por cada zona antes de day."""
    counts = {z: 0 for z in range(1, 7)}
    for d in sorted(cron):
        if d >= day:
            break
        for z in range(1, 7):
            if cron.get(d, {}).get(f'ZONA_{z}') == agent:
                counts[z] += 1
    return counts


def _would_repeat_previous_day(cron, day, zone_key, agent):
    """Indica si agent quedaría en la misma zona que el día anterior."""
    return cron.get(day - 1, {}).get(zone_key) == agent


def _repair_secondary_zone_rotation(self):
    """Aplica la opción 2 de rotación de zonas secundarias.

    Prioridad:
      1. CASTRO D. nunca se mueve.
      2. Evitar que un agente repita la misma zona en días consecutivos.
      3. Preferir el intercambio que coloque a cada agente en una zona
         que haya realizado menos veces históricamente.
      4. Si hay varias opciones equivalentes, elegir la que reduzca más
         las repeticiones y mejore la dispersión de zonas.

    Solo intercambia agentes que ya están asignados ese mismo día. Por eso
    no altera disponibilidad, licencias, cantidad de turnos, horas, pagos
    ni puestos de aeropuerto.
    """
    if not self.result:
        return 0

    cron = self.result.get('cron', {})
    admin = self.admin
    repairs = 0

    for day in sorted(cron):
        if day <= 1:
            continue

        today = cron.get(day, {})
        zone_keys = [f'ZONA_{z}' for z in range(1, 7) if today.get(f'ZONA_{z}')]

        # Hacemos varias pasadas porque un intercambio puede permitir
        # solucionar otra repetición del mismo día.
        changed = True
        while changed:
            changed = False

            for key in list(zone_keys):
                agent = today.get(key)
                if not agent or agent == admin:
                    continue

                # Este agente no repite su zona anterior: no hay nada que corregir.
                if not _would_repeat_previous_day(cron, day, key, agent):
                    continue

                current_zone = int(key.split('_')[1])
                best = None

                for other_key in zone_keys:
                    if other_key == key:
                        continue

                    other_agent = today.get(other_key)
                    if not other_agent or other_agent == admin or other_agent == agent:
                        continue

                    other_zone = int(other_key.split('_')[1])

                    # Después del intercambio, ninguno debe quedar repetido
                    # en la zona que recibe.
                    if _would_repeat_previous_day(cron, day, other_key, agent):
                        continue
                    if _would_repeat_previous_day(cron, day, key, other_agent):
                        continue

                    # Historial previo: favorecemos la zona menos utilizada
                    # por cada agente. Menor valor = mejor rotación.
                    a_counts = _zone_counts_before_day(cron, day, agent)
                    b_counts = _zone_counts_before_day(cron, day, other_agent)

                    # También favorecemos que ambos salgan de su zona actual
                    # si esa zona es la que vienen repitiendo.
                    score = (
                        a_counts[other_zone] + b_counts[current_zone],
                        max(a_counts[other_zone], b_counts[current_zone]),
                        a_counts[other_zone],
                        b_counts[current_zone],
                        abs(a_counts[other_zone] - b_counts[current_zone]),
                    )

                    if best is None or score < best[0]:
                        best = (score, other_key, other_agent)

                if best is not None:
                    _, other_key, other_agent = best
                    today[key], today[other_key] = other_agent, agent
                    repairs += 1
                    changed = True
                    break

    if repairs:
        # Mantiene los contadores internos coherentes con el cronograma final.
        self.recalculate_counts()

    return repairs


def _generate_with_secondary_zone_rotation(self):
    # Generación original de v5: no se modifica.
    _original_generate(self)

    # Aplicación posterior y local de la opción 2.
    if self.result:
        repairs = _repair_secondary_zone_rotation(self)
        if repairs:
            self.refresh_schedule()
            self.status.set(
                f'Cronograma generado. Se realizaron {repairs} ajuste(s) de rotación en zonas secundarias; CASTRO no fue modificado.'
            )


GiroApp.generate = _generate_with_secondary_zone_rotation


if __name__ == '__main__':
    root = tk.Tk()
    GiroApp(root)
    root.mainloop()
