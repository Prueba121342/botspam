import time
import datetime
import psutil
import threading

# Variable global para controlar el estado del bot
bot_activo = True

def iniciar_bot():
    global bot_activo
    bot_activo = True
    print("Bot iniciado.")
    # Aquí se llamará a la función del código principal del bot
    while bot_activo:
        print("El bot está ejecutándose...")
        time.sleep(5)  # Simulación del trabajo del bot

def detener_bot():
    global bot_activo
    if bot_activo:
        bot_activo = False
        print("✔️ Bot detenido correctamente.")
    else:
        print("⚠️ El bot ya está detenido.")

def verificar_bateria():
    battery = psutil.sensors_battery()
    if battery and battery.percent < 20 and not battery.power_plugged:
        return True
    return False

def gestor_tiempos():
    while True:
        ahora = datetime.datetime.now()

        # Verificar si estamos dentro del periodo de 2:30 AM a 4:30 AM
        if ahora.hour == 2 and ahora.minute == 30:
            detener_bot()
            print("⏰ Deteniendo el bot hasta las 4:30 AM.")
            time.sleep(2 * 60 * 60)  # Dormir por 2 horas hasta las 4:30 AM
            iniciar_bot()

        # Verificar si estamos dentro del periodo de cada 3 horas
        if ahora.hour % 3 == 0 and ahora.minute == 0:
            detener_bot()
            print(f"⏰ Deteniendo el bot por 20 minutos.")
            time.sleep(20 * 60)  # Dormir por 20 minutos
            iniciar_bot()

        # Verificar la batería
        if verificar_bateria():
            detener_bot()
            print("⚠️ Batería baja. Deteniendo el bot.")
            while verificar_bateria():
                time.sleep(60)  # Esperar un minuto y verificar de nuevo
            iniciar_bot()

        time.sleep(60)  # Verificar cada minuto

def iniciar_gestor():
    # Iniciar el gestor de tiempos en un hilo separado
    hilo_gestor = threading.Thread(target=gestor_tiempos, daemon=True)
    hilo_gestor.start()
