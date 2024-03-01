import os
import asyncio
import logging
import aiofiles
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from models_pruebas import SendMessageRequest, IncomingMessage, SendMessageTemplateRequest, Component
import httpx
from httpx import HTTPError, AsyncClient, HTTPStatusError, ConnectTimeout
from typing import Optional


router= APIRouter()

async def process_message(message):
    """
    Procesa de manera asíncrona un mensaje individual recibido a través del webhook.
    Esta función está diseñada para manejar diferentes tipos de mensajes, enfocándose específicamente en mensajes
    que contienen medios, como imágenes, videos, etc., extrayendo información relevante e iniciando pasos de
    procesamiento adicionales.

    Args:
        message: Un objeto que representa el mensaje recibido. Se espera que este objeto tenga varios atributos
                 dependiendo de su tipo (por ejemplo, texto, imagen, video), incluyendo, pero no limitado a, un ID
                 para medios, tipo MIME, nombre de archivo y subtítulo.

    La función emplea programación defensiva inicializando variables de antemano para evitar errores de referencia.
    También maneja excepciones de manera elegante para asegurar que un mensaje fallido no interrumpa el flujo de
    procesamiento general.
    """
    try:
        # Inicializar variables para asegurar que están definidas incluso si no son establecidas por el mensaje.
        # Esto previene errores de referencia durante las verificaciones condicionales y el procesamiento.
        media_id = None
        mime_type = None
        filename = None
        caption = None

        # Verificar si el objeto mensaje tiene un atributo nombrado según su tipo (por ejemplo, 'image', 'video')
        # y extraer información relevante si está presente.
        if hasattr(message, message.type):
            media_section = getattr(message, message.type)
            media_id = getattr(media_section, 'id', None)
            mime_type = getattr(media_section, 'mime_type', '').split("/")[-1] if hasattr(media_section, 'mime_type') else None
            filename = getattr(media_section, 'filename', None)
            caption = getattr(media_section, 'caption', None)

        # Proceder con el procesamiento si se presenta un ID de medio, indicando un mensaje de medio.
        if media_id:
            logging.info(f"Procesando mensaje de tipo '{message.type}' con media_id '{media_id}'")
            #await handle_media_message(media_id, message.type, mime_type, filename, caption)
        else:
            # Registrar una advertencia si no se encuentra un ID de medio, indicando que el mensaje puede no requerir
            # procesamiento o no ser compatible con la lógica actual.
            logging.warning(f"Mensaje recibido sin media_id. Tipo de mensaje: '{message.type}'")
    except Exception as e:
        # Registrar cualquier excepción encontrada durante el procesamiento del mensaje.
        # Esto ayuda a identificar problemas sin detener el procesamiento de mensajes subsiguientes.
        logging.error(f"Error al procesar mensaje: {e}")
        # Dependiendo de las necesidades de la aplicación, podrías querer volver a lanzar excepciones o manejarlas
        # de manera silenciosa. Esta decisión debe basarse en la criticidad de procesar cada mensaje con éxito.

@router.post("/webhook", status_code=200)
async def receive_message(request: IncomingMessage):
    """
    Este método actúa como el punto de entrada para los mensajes entrantes a través del webhook.
    Es invocado por un sistema externo (e.g., WhatsApp Business API) cuando se reciben nuevos mensajes o eventos.
    
    La función está diseñada para ser asincrónica, lo que permite manejar múltiples mensajes de manera eficiente
    sin bloquear el servidor, mejorando así la escalabilidad de la aplicación.

    Args:
        request (IncomingMessage): Un objeto IncomingMessage que contiene los detalles del mensaje entrante,
                                   conforme al modelo Pydantic definido. Este objeto facilita la validación y el manejo
                                   de los datos recibidos.

    Returns:
        JSONResponse: Una respuesta HTTP indicando el resultado del procesamiento del mensaje. Devuelve un estado
                      de éxito junto con un mensaje correspondiente en caso de éxito, o un estado de error en caso de fallo.
    """
    try:
        # Conversión del cuerpo de la solicitud a un diccionario para facilitar el registro y la depuración.
        # Es importante asegurar que el modelo IncomingMessage tenga un método 'dict()' para esta conversión.
        logging.info(f"*")
        logging.info(f"*")
        logging.info(f"*")
        logging.info(f"*")
        logging.info(f"*")
        logging.info(f"*")
        logging.info(f"*")
        logging.info(f"*")
        logging.info(f"*")
        logging.info(f"*")
        logging.info(f"*")
        logging.info(f"ESTO ES LO QUE LLEGA AL CLIENTE: {request}")
        request_data = request.model_dump()
        logging.info(f"Evento recibido: {request_data}")

        # Lista para acumular tareas asincrónicas correspondientes al procesamiento de cada mensaje.
        tasks = []

        # Iteración a través de cada entrada en el mensaje recibido. Cada 'entry' puede representar
        # diferentes mensajes o eventos que necesitan ser procesados.
        for entry in request.entry:
            for change in entry.changes:
                # Verificación de la presencia de mensajes en el cambio actual para procesar.
                if change.value.messages:
                    # Programación de una tarea asincrónica para cada mensaje encontrado.
                    # Esto permite un procesamiento concurrente y eficiente de múltiples mensajes.
                    for message in change.value.messages:
                        tasks.append(process_message(message))
                elif change.value.statuses:
                    for statuses in change.value.statuses:
                        logging.info(f"Actualización de estado: {statuses.status}")

        # Si hay tareas programadas, se ejecutan de manera concurrente.
        # Esto es crucial para mantener la eficiencia y la capacidad de respuesta del servicio.
        if tasks:
            await asyncio.gather(*tasks)
            logging.info("Todas las tareas procesadas con éxito.")

        # Respuesta exitosa tras el procesamiento de los mensajes.
        return JSONResponse(content={"status": "success", "message": "Evento procesado con éxito"}, status_code=status.HTTP_200_OK)
    except ConnectTimeout as e:
        logging.error("Connection timeout")
        return JSONResponse(content={"status": "error", "message": "Timeout de conexión"}, status_code=status.HTTP_504_GATEWAY_TIMEOUT)
    except HTTPStatusError as e:
        logging.error(f"Ha ocurrido un error no manejado: {e.response.status_code}")
        return JSONResponse(content={"status": "error", "message": "Error, favor tomar aaa de la actividad enviada y comunicarse con el supldior"}, status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        # Registro de cualquier excepción ocurrida durante el procesamiento.
        # Es importante capturar y registrar excepciones para facilitar la depuración y mantenimiento.
        logging.error(f"Error al procesar el mensaje: {e}")

        # Respuesta indicando fallo en el procesamiento debido a la excepción capturada.
        # Devolver un mensaje de error específico puede ayudar en la identificación rápida del problema.
        return JSONResponse(content={"status": "error", "message": "Error al procesar evento"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)