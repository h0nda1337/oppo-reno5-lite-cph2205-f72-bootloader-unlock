# Evidencia sanitizada del caso probado

Fecha: 11 de octubre de 2026. Una unidad del propietario, sin cuentas Google ni bloqueo de pantalla. Los extractos siguientes se seleccionaron de los registros originales; se omitieron seriales, rutas locales, claves, hashes de bloques personales y logs completos.

## Identidad y estado inicial

```text
manufacturer: OPPO
model: CPH2205
device: OP4F43L1
platform: mt6779
build: CPH2205_11_F.72
Android: 13
ro.boot.flash.locked=1
ro.boot.verifiedbootstate=green
ro.boot.vbmeta.device_state=locked
sys.oem_unlock_allowed=0
ro.frp.pst=/dev/block/by-name/frp
```

## Acceso y respaldos

- Preloader por puerto serie, transición a BootROM y carga de DA XFLASH.
- MT6779, código `0x725`; SBC activado, SLA desactivado, DAA activado.
- Payload MT6779 y exploit kamakiri2 por defecto en la revisión fijada de MTKClient.
- Almacenamiento UFS, bloque de 4096 bytes; boot1 y boot2 de 4 MiB cada uno.
- GPT leída; CRC de cabecera y tabla de entradas de las copias principal y secundaria comprobados.
- Respaldos seleccionados: tamaños y SHA-256 verificados. Las copias independientes de seccfg y frp eran idénticas.

## Intento directo con seccfg

```text
Estado original en la cabecera de seccfg: 1
Candidato generado: 3
Algoritmo reconocido por MTKClient: V4
Escritura de 512 bytes: exitosa
Lectura inmediata: idéntica al candidato
Resto de seccfg: idéntico al original
```

Después del arranque, Android continuó reportando `locked` y la cabecera de seccfg contenía estado 4. Se extrajo del registro del propio teléfono esta línea de diagnóstico:

```text
double_check_lock_state: seccfg_lock_state is 0, rpmb_lock_state is 1, so need change seccfg state
```

El `0/1` de ese mensaje es el estado que usa la función LK; no es el valor bruto `3/4` de la cabecera. La evidencia respalda que el flujo directo no bastó y que había una comprobación adicional con RPMB. No se escribió, borró o inicializó RPMB directamente desde las herramientas.

## Preparación y escritura de la segunda ruta

```text
boot1 original: 4194304 bytes, UFS_BOOT
Offset original del preloader: 0x1000
Offset del preloader en el candidato: 0x2000
ROMINFO original: 0x12ec; bandera 0x22
Preloader extraído: 353444 bytes
Preloader extraído conservado después de reubicar: idéntico
boot1 tras escritura: idéntico al candidato
boot2: sin modificar

frp: 1048576 bytes
Dos lecturas originales: idénticas
Checksum original: válido
Cabecera AOSP: 0x19901873, longitud de datos 0
Último byte OEM: 0 -> 1
Cambio adicional: checksum SHA-256, bytes 0..31
Otros bytes conservados: sí
frp tras escritura: idéntico al candidato
```

Android arrancó después del parche y confirmó `sys.oem_unlock_allowed=1`.

## Fastboot y desbloqueo

```text
product: k79v1_64
is-userspace: no
unlocked: no
(bootloader) unlock_ability = 16777216

fastboot flashing unlock:
(bootloader) Start unlock flow
OKAY [ 18.798s]

Consultas posteriores:
unlocked: yes
secure: no
```

Se envió `fastboot reboot`. El propietario observó Orange State y un posible formateo. El flujo Fastboot contempla restablecer los datos y fue necesario autorizar de nuevo ADB; no se auditó el contenido de userdata antes y después para cuantificar el borrado.

## Android después del reinicio

```text
ro.product.model=CPH2205
ro.build.display.id=CPH2205_11_F.72
sys.boot_completed=1
ro.boot.flash.locked=0
ro.boot.verifiedbootstate=orange
ro.boot.vbmeta.device_state=unlocked
sys.oem_unlock_allowed=1
ro.bootmode=normal
```

Esta es la verificación que confirmó el objetivo: bootloader desbloqueado, estado conservado en el arranque siguiente y Android funcionando. No se instalaron root, recovery o firmware personalizados. No se probaron otras unidades, OTA ni recuperación tras un fallo deliberado del preloader.
