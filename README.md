# OPPO Reno5 Lite CPH2205 F.72 — desbloqueo del bootloader

**Desbloqueo confirmado en un OPPO Reno5 Lite CPH2205 con Android 13 y firmware `CPH2205_11_F.72`.** Android arrancó correctamente y conservó el estado desbloqueado después del reinicio.

Este repositorio documenta un caso probado el **11 de octubre de 2026**, con autorización del propietario. No es una garantía de compatibilidad con otros firmwares, unidades o modelos, ni una herramienta que desbloquee automáticamente el teléfono.

La ruta que funcionó fue:

1. Acceder a BootROM con MTKClient y respaldar el propio dispositivo.
2. Preparar el parche de Fastboot usando **el preloader original de esa unidad**.
3. Habilitar el permiso OEM, que no aparecía en Opciones de desarrollador, conservando los demás datos del bloque persistente y recalculando su checksum.
4. Escribir y leer de nuevo ambos candidatos para verificar cada byte.
5. Ejecutar `fastboot flashing unlock` y comprobar el resultado después de arrancar Android.

El exploit y el parche son de los proyectos citados abajo. Nuestra contribución es documentar la combinación que funcionó en F.72, el diagnóstico del bloqueo adicional y las comprobaciones realizadas.

## Resultado comprobado

| Comprobación | Antes | Después |
|---|---|---|
| Android `ro.boot.flash.locked` | `1` | `0` |
| Android `ro.boot.verifiedbootstate` | `green` | `orange` |
| Android `ro.boot.vbmeta.device_state` | `locked` | `unlocked` |
| Android `sys.oem_unlock_allowed` | `0` | `1` |
| Android `sys.boot_completed` | `1` | `1` |
| Fastboot `getvar unlocked` | `no` | `yes` |
| Fastboot `getvar secure` | `yes` | `no` |

Véase [la evidencia sanitizada](docs/VERIFICATION.md), [la guía paso a paso](docs/METHOD.md) y [las notas de recuperación](docs/RECOVERY.md).

## Por qué no bastó con `seccfg unlock`

MTKClient consiguió acceso a BootROM y escribió un `seccfg` válido con estado 3. La lectura inmediata confirmó la escritura. Sin embargo, al arrancar Android seguía bloqueado y la siguiente lectura encontró estado 4.

El registro del propio teléfono mostró que LK comparaba ese estado con RPMB y lo volvía a bloquear. Por eso habilitamos Fastboot y usamos el flujo de desbloqueo del propio bootloader. **No borramos RPMB.** Véase [el diagnóstico](docs/VERIFICATION.md#intento-directo-con-seccfg).

## Alcance y precauciones

- Se probó **una unidad**, con MT6779 y almacenamiento UFS. No aplicar a ciegas en otro modelo o versión.
- Modificar el preloader puede impedir el arranque. Obtener y verificar respaldos propios y una ruta viable de recuperación antes de escribir.
- El desbloqueo puede restablecer los datos de usuario. No usar este procedimiento para conservar datos sin respaldo.
- No usar el preloader de otra unidad ni borrar RPMB, NVRAM, NVDATA, persist o calibraciones para resolver un error.
- Orange State es la advertencia esperada de un dispositivo desbloqueado; no indica por sí sola un fallo de Android. [Documentación de Verified Boot](https://source.android.com/docs/security/features/verifiedboot/boot-flow).
- Una OTA puede sobrescribir el parche del preloader y cerrar el acceso Fastboot, según el proyecto del parche. No se probó una OTA después del desbloqueo.
- No volver a bloquear después de instalar imágenes modificadas sin restaurar primero el firmware firmado compatible.

Se conserva Android original: este procedimiento no instala root, recovery personalizado ni ROM.

## Herramientas incluidas

Los dos scripts de `tools/` usan únicamente la biblioteca estándar de Python 3.10 o posterior. **Solo trabajan sobre archivos locales; no ejecutan ADB, Fastboot ni escrituras al teléfono.**

- `prepare_oem_permission.py`: exige dos respaldos idénticos de frp de 1 MiB, checksum correcto, cabecera conocida y bloque de datos FRP vacío. Prepara el permiso OEM y el checksum nuevo. Requiere `--enable-oem-unlock` y rechaza sobrescribir archivos.
- `audit_preloader.py`: compara dos respaldos de boot1, el preloader extraído y el candidato producido por el parche upstream. Rechaza cambios inesperados en el código, ROMINFO o BRLYT. Comprueba identidad de bytes; no verifica criptográficamente la firma del fabricante ni garantiza que un teléfono arranque.

Las pruebas usan datos sintéticos y no se comunican con ningún dispositivo:

```powershell
python -m unittest discover -s tests -v
```

## Créditos y fuentes

- **bkerler y colaboradores — [MTKClient](https://github.com/bkerler/mtkclient)**: acceso MediaTek, kamakiri2, payload MT6779 y agente XFLASH. Revisión utilizada: `cd25cf9c1ff6d36e82697ac2c798e69e9cfb78c3`.
- **Shocked-Cat / Max_Goblin y colaboradores — [oppo-mtk-fastboot-unlock](https://github.com/Shocked-Cat/oppo-mtk-fastboot-unlock)**: parche del preloader para habilitar Fastboot. Revisión utilizada: `ecf8e2c6f967706e6ab55c4774141abb5d78d12f`. [Lista de modelos](https://github.com/Shocked-Cat/oppo-mtk-fastboot-unlock/blob/ecf8e2c6f967706e6ab55c4774141abb5d78d12f/support_list.md).
- **Android Open Source Project — [PersistentDataBlockService de Android 13](https://github.com/aosp-mirror/platform_frameworks_base/blob/android-13.0.0_r1/services/core/java/com/android/server/PersistentDataBlockService.java)**: posición del permiso OEM y cálculo del checksum.
- **Android Open Source Project — [desbloqueo del bootloader](https://source.android.com/docs/core/architecture/bootloader/locking_unlocking)** y [estados de Verified Boot](https://source.android.com/docs/security/features/verifiedboot/boot-flow).

No se distribuyen herramientas upstream, firmware, respaldos, imágenes parcheadas ni registros completos del dispositivo. Véase [NOTICE](NOTICE.md). Los archivos originales de este repositorio se publican bajo AGPL-3.0; cada proyecto citado conserva su propia licencia.
