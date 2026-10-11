# Recuperación y límites de los respaldos

Modificar boot1 puede impedir que el teléfono arranque. Antes de escribir, verificar la identidad y disponer del boot1 completo original, boot2, preloader extraído, frp, seccfg, GPT y particiones críticas propias. No usar archivos publicados de otro teléfono.

En el caso probado se confirmó acceso al BootROM y al agente XFLASH, se conservó el preloader extraído para inicializar DRAM y no se modificó boot2. **No se provocó un fallo deliberado del preloader para comprobar la recuperación.** Una auditoría de bytes y un respaldo no garantizan por sí solos que la recuperación esté disponible en cualquier unidad.

## Si no arranca tras el parche

1. Desconectar USB y preparar MTKClient antes de reconectar el teléfono apagado. Usar la combinación de ambos botones de volumen descrita en la guía.
2. Confirmar que se alcanza BootROM del MT6779 y se carga el agente. Si fuera necesario inicializar DRAM, usar `--preloader` con el RAW **original extraído de esa unidad**, siguiendo las instrucciones de la revisión de MTKClient utilizada.
3. Verificar hashes y tamaños de los originales; restaurar únicamente las regiones cambiadas y sus destinos comprobados.
4. Leer cada región restaurada y compararla con el original antes de reiniciar.

Si BootROM/DA no es accesible, **detener las escrituras**. Revisar conexión y controladores y buscar una recuperación documentada para esa unidad. No borrar regiones para intentar forzar la conexión.

## Destinos del caso probado

Estos valores describen la GPT de la unidad probada. **No se deben reutilizar sin leer y verificar la GPT y geometría del dispositivo objetivo.** Preferir comandos por nombre de partición.

| Original | Destino | Offset observado | Tamaño |
|---|---|---:|---:|
| boot1-full.bin | UFS boot1 | 0 | 4194304 bytes |
| frp-original.bin | frp, UFS user | 0x0de08000 | 1048576 bytes |
| seccfg-original.bin | seccfg, UFS user | 0x17800000 | 524288 bytes |

Con una sesión DA válida, los comandos equivalentes de restauración son:

```powershell
& $Py $Mtk wf "$Backup\boot1-full.bin" --parttype boot1
& $Py $Mtk w frp "$Backup\frp-original.bin"
```

Restaurar seccfg solo cuando corresponda al plan de recuperación y al firmware instalado. Cambiarlo a bloqueado después de instalar imágenes personalizadas puede impedir el arranque; además, esta unidad mantiene un estado adicional en RPMB. No tratar una copia antigua de seccfg como un método universal de relock.

Restaurar el preloader original puede volver a cerrar el acceso a Fastboot. No se comprobó qué efecto tendría una restauración de preloader posterior al desbloqueo sobre todas las funciones del equipo.

Los respaldos seleccionados no son una imagen completa de super, userdata ni RPMB. El restablecimiento de datos de usuario durante el desbloqueo no se deshace restaurando boot1 o frp. No formatear boot1, boot2, RPMB, NVRAM, NVDATA, persist o calibraciones como solución genérica.
