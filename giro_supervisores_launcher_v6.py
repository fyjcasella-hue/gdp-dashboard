# Giro de Supervisores - Nelson Casella
# Corrección puntual: rotación de zonas secundarias.
# Se conserva íntegramente la lógica estable de v5 y solo se agrega
# una reparación local posterior a la generación para evitar que un
# mismo agente repita la misma ZONA SECUNDARIA en días consecutivos.

import tkinter as tk
from giro_supervisores_launcher_v5 import GiroApp


_original_generate = GiroApp.generate


def _repair_secondary_zone_rotation(self):
    """Evita repeticiones consecutivas en la misma zona secundaria.

    No toca a CASTRO ni modifica cantidades de turnos, pagos, licencias,
    descansos, aeropuerto ni la equidad general. Solo intercambia zonas
    entre dos agentes ya asignados al mismo día cuando ello elimina una
    repetición consecutiva de zona para ambos.
    """
    if not self.result:
        return 0

    cron = self.result.get('cron', {})
    admin = self.admin
    repairs = 0

    for day in sorted(cron):
        if day <= 1:
            continue

        previous = cron.get(day - 1, {})
        today = cron.get(day, {})
        zone_keys = [f'ZONA_{z}' for z in range(1, 7) if f'ZONA_{z}' in today]

        # Si un agente repite exactamente la misma zona del día anterior,
        # buscamos otro agente del mismo día con quien intercambiar zonas.
        for key in list(zone_keys):
            agent = today.get(key)

            # CASTRO conserva su giro original y nunca se mueve.
            if not agent or agent == admin:
                continue

            if previous.get(key) != agent:
                continue

            for other_key in zone_keys:
                if other_key == key:
                    continue

                other_agent = today.get(other_key)
                if not other_agent or other_agent == admin or other_agent == agent:
                    continue

                # El intercambio debe mejorar, no crear otra repetición:
                # agent -> other_key y other_agent -> key.
                if previous.get(other_key) == agent:
                    continue
                if previous.get(key) == other_agent:
                    continue

                today[key], today[other_key] = other_agent, agent
                repairs += 1
                break

    if repairs:
        # Recalcula el historial de zonas después de los intercambios.
        # Los conteos de turnos y horas se mantienen, pero esta llamada
        # deja todos los antecedentes internos perfectamente consistentes.
        self.recalculate_counts()

    return repairs


def _generate_with_secondary_zone_rotation(self):
    # Ejecuta el generador probado de v5 sin alterar su lógica.
    _original_generate(self)

    # Si la generación fue exitosa, corrige únicamente las repeticiones
    # consecutivas de zonas secundarias.
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
