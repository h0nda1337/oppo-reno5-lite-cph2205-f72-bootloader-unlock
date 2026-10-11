# Método probado en CPH2205_11_F.72

## 1. Entorno y diagnóstico

La sesión se realizó en Windows, con Python 3.11.9, Git, ADB/Fastboot, UsbDk y MTKClient 2.1.4 en la revisión indicada. Consultar las instrucciones de Windows del [MTKClient fijado](https://github.com/bkerler/mtkclient/blob/cd25cf9c1ff6d36e82697ac2c798e69e9cfb78c3/README-WINDOWS.md) para instalar controladores y dependencias.

Con un único dispositivo conectado y ADB autorizado:

```powershell
adb devices -l
adb shell getprop ro.product.model
adb shell getprop ro.board.platform
adb shell getprop ro.build.display.id
adb shell getprop ro.boot.flash.locked
adb shell getprop ro.boot.verifiedbootstate
adb shell getprop ro.boot.vbmeta.device_state
adb shell getprop sys.oem_unlock_allowed
adb shell getprop ro.frp.pst
```

En el caso probado: `CPH2205`, `mt6779`, `CPH2205_11_F.72`, bloqueo `1`, Verified Boot `green`, vbmeta `locked`, permiso OEM `0` y bloque persistente `/dev/block/by-name/frp`. La opción Desbloqueo OEM no aparecía. El propietario confirmó que no había cuentas Google ni PIN, patrón o contraseña.

**El primer `adb reboot bootloader` volvió a Android sin exponer Fastboot utilizable.** No confundir este resultado con falta de acceso a BootROM.

Mantener los respaldos fuera del repositorio y en una unidad con espacio suficiente. Las siguientes rutas son ejemplos privados relativos a la raíz del repositorio, no rutas del equipo usado en la prueba.

```powershell
New-Item -ItemType Directory -Force .\private\backups, .\private\candidates, .\private\session | Out-Null
git clone https://github.com/bkerler/mtkclient.git .\private\mtkclient
git -C .\private\mtkclient checkout cd25cf9c1ff6d36e82697ac2c798e69e9cfb78c3
git clone https://github.com/Shocked-Cat/oppo-mtk-fastboot-unlock.git .\private\oppo-mtk-fastboot-unlock
git -C .\private\oppo-mtk-fastboot-unlock checkout ecf8e2c6f967706e6ab55c4774141abb5d78d12f
python -m venv .\private\venv
.\private\venv\Scripts\python.exe -m pip install -r .\private\mtkclient\requirements.txt
$Repo = (Get-Location).Path
$Py = (Resolve-Path .\private\venv\Scripts\python.exe).Path
$Mtk = (Resolve-Path .\private\mtkclient\mtk.py).Path
$Backup = Join-Path $Repo 'private\backups'
$Candidate = Join-Path $Repo 'private\candidates'
Set-Location .\private\session
```

No renombrar particiones por analogía con otro modelo. Detenerse si la identificación, geometría UFS, GPT o cabeceras difieren de lo esperado.

## 2. Acceso MediaTek

Preparar la escucha **antes** de conectar el teléfono apagado:

```powershell
& $Py $Mtk printgpt --serialport DETECT --write_preloader_to_file
```

La combinación que funcionó fue:

1. Desconectar USB y apagar por completo desde Android.
2. Esperar 10 segundos.
3. Mantener Volumen + y Volumen − simultáneamente.
4. Conectar USB sin soltarlos, mantener unos 20 segundos y después soltar. No pulsar Encendido en este intento.

En la sesión, el preloader fue detectado por puerto serie; MTKClient consiguió pasar a BootROM y cargar el agente XFLASH por USB. El registro identificó MT6779 (`0x725`), SBC activado, SLA desactivado y DAA activado. El exploit por defecto fue kamakiri2 con el payload MT6779.

Esperar a que MTKClient termine la lectura de GPT y conservar el directorio de sesión y su `.state` para las operaciones posteriores. El número COM depende del PC. No ejecutar varias instancias de MTKClient simultáneamente ni conectar otro teléfono.

## 3. Respaldos antes de escribir

Estas lecturas se realizaron con el agente ya conectado:

```powershell
& $Py $Mtk rf "$Backup\boot1-full.bin" --parttype boot1
& $Py $Mtk rf "$Backup\boot1-verification.bin" --parttype boot1
& $Py $Mtk rf "$Backup\boot2-full.bin" --parttype boot2
& $Py $Mtk r seccfg "$Backup\seccfg-original.bin"
& $Py $Mtk r seccfg "$Backup\seccfg-verification.bin"
& $Py $Mtk r frp "$Backup\frp-original.bin"
& $Py $Mtk r frp "$Backup\frp-verification.bin"
```

En el dispositivo probado, boot1 y boot2 tenían 4 MiB cada uno; seccfg 512 KiB y frp 1 MiB. También se respaldaron GPT principal y secundaria, preloader extraído y particiones de arranque y seguridad, incluidas boot, recovery, LK/LK2, TEE, vbmeta, dtbo, NVRAM, NVDATA y persist. Se verificaron tamaños, SHA-256 y CRC de GPT.

Ejemplo de lecturas adicionales:

```powershell
foreach ($Partition in @('boot','recovery','lk','lk2','tee1','tee2','vbmeta','vbmeta_system','vbmeta_vendor','dtbo','nvram','nvdata','nvcfg','persist','protect1','protect2','sec1','proinfo','oppo_custom','metadata','misc','para')) {
    & $Py $Mtk r $Partition "$Backup\$Partition.bin"
}
```

Conservar asimismo las particiones OPPO de reserva y configuración que existan en la GPT de la unidad. Calcular y guardar los hashes fuera del repositorio. Un código de salida de cero no sustituye a comprobar el tamaño y el contenido de cada archivo. Respaldar datos personales por separado: esto no es un respaldo completo de userdata o super.

`--write_preloader_to_file` produjo `preloader_k79v1_64.bin` en el caso probado. Guardar ese archivo con los respaldos y comprobar que sus bytes aparecen dentro de boot1. Si el nombre o estructura difieren, no asumir compatibilidad.

```powershell
Copy-Item -LiteralPath .\preloader_k79v1_64.bin -Destination "$Backup\preloader_k79v1_64.bin"
```

Para la GPT, se guardó la región inicial y el final real de la UFS user. La geometría observada fue de `0x1dcb000000` bytes, con bloques de 4096 bytes. Las lecturas de esta unidad fueron `ro 0 0x8000` y `ro 0x1dcafe0000 0x20000`, con archivos de salida propios. Comprobar la geometría antes de reutilizar esos offsets y validar los CRC de las dos cabeceras y tablas. El archivo llamado `gpt_backup.bin` que genera esa revisión de MTKClient es una porción de la lectura inicial; no debe confundirse con una lectura independiente de la GPT secundaria al final del dispositivo.

## 4. Diagnóstico del intento directo

Se probó el comando documentado `da seccfg unlock`. La escritura inmediata y su checksum se verificaron, pero después del arranque LK lo volvió a bloquear por su comprobación con RPMB. **Ese intento no es un paso requerido para la ruta de Fastboot y no se recomienda repetirlo para forzar el resultado.**

No borrar ni inicializar RPMB como alternativa. Véase [evidencia](VERIFICATION.md).

## 5. Preparar el parche del preloader original

Usar el script upstream, fijado a la revisión citada, sobre el respaldo **completo de boot1 de la propia unidad**, no sobre otro firmware o un RAW suelto:

```powershell
Set-Location $Candidate
& $Py "$Repo\private\oppo-mtk-fastboot-unlock\path_preloader.py" "$Backup\boot1-full.bin" boot1-fastboot.bin
```

El script deja el resultado en `preloader_path\boot1-fastboot.bin` y puede pedir Enter al finalizar. No aceptar excepciones sobre tamaño, tipo de memoria o ausencia de ROMINFO. En el caso probado, el código empezaba en `0x1000`, ROMINFO en `0x12ec`, la bandera era `0x22` y el final descartado estaba vacío.

Auditar el candidato sin escribir al teléfono:

```powershell
& $Py "$Repo\tools\audit_preloader.py" "$Backup\boot1-full.bin" "$Backup\boot1-verification.bin" "$Backup\preloader_k79v1_64.bin" "$Candidate\preloader_path\boot1-fastboot.bin"
```

La auditoría exige la estructura observada en esta prueba y comprueba la reubicación exacta, cabecera BRLYT, copia de ROMINFO y conservación del preloader extraído. Que pase no garantiza el arranque; es una comprobación de integridad, no una validación criptográfica de firma ni una prueba de compatibilidad universal.

## 6. Preparar el permiso OEM cuando no existe el interruptor

Si la opción OEM está disponible, preferir el ajuste del propio Android. En este caso no aparecía y `sys.oem_unlock_allowed=0`.

Los dos respaldos de frp tenían el formato de PersistentDataBlockService de Android 13, checksum correcto y longitud de datos FRP cero. Según [AOSP](https://github.com/aosp-mirror/platform_frameworks_base/blob/android-13.0.0_r1/services/core/java/com/android/server/PersistentDataBlockService.java), el permiso OEM ocupa el último byte y el checksum es SHA-256 del bloque con sus primeros 32 bytes puestos a cero.

```powershell
& $Py "$Repo\tools\prepare_oem_permission.py" "$Backup\frp-original.bin" "$Backup\frp-verification.bin" "$Candidate\frp-oem-enabled.bin" --enable-oem-unlock
```

El script cambia solo el último byte de `0` a `1` y los 32 bytes del checksum. Rechaza cabeceras desconocidas, checksum incorrecto, respaldos diferentes, longitud de datos FRP no vacía y sobrescrituras. **No borra FRP ni cuentas, ni elimina bloqueos de acceso.** El caso probado era del propietario, sin cuentas Google ni bloqueo de pantalla. No extrapolar a equipos con datos o restricciones de cuenta.

Android puede reformatear el bloque persistente cuando OEM unlock está habilitado; eso forma parte de la implementación AOSP. Mantener el original y un respaldo de datos personales.

## 7. Escritura y lectura de comprobación

Solo continuar con candidatos auditados, respaldo completo, destino verificado y recuperación viable. Las escrituras son críticas y se hacen bajo responsabilidad del propietario. En la sesión original se usó la API de MTKClient, comprobando que ambos originales vivos coincidían con los respaldos antes de escribir. Estos son los comandos equivalentes de su CLI, no una segunda prueba independiente:

```powershell
Set-Location "$Repo\private\session"
& $Py $Mtk w frp "$Candidate\frp-oem-enabled.bin"
& $Py $Mtk r frp "$Backup\frp-readback.bin"
& $Py $Mtk wf "$Candidate\preloader_path\boot1-fastboot.bin" --parttype boot1
& $Py $Mtk rf "$Backup\boot1-readback.bin" --parttype boot1
```

Comparar cada lectura **byte por byte y por SHA-256** con su candidato. Detenerse ante diferencias. No modificar boot2, LK, vbmeta o calibraciones. No formatear ninguna región de arranque para intentar corregir un error.

```powershell
Get-FileHash "$Candidate\frp-oem-enabled.bin", "$Backup\frp-readback.bin" -Algorithm SHA256
Get-FileHash "$Candidate\preloader_path\boot1-fastboot.bin", "$Backup\boot1-readback.bin" -Algorithm SHA256
& $Py $Mtk reset
```

Desconectar USB, esperar 5 segundos, encender normalmente y reconectar. Comprobar que Android termina de arrancar y `sys.oem_unlock_allowed=1`. En esta prueba seguía bloqueado en ese punto, lo esperado antes de Fastboot.

## 8. Desbloquear desde Fastboot

Con ADB autorizado y un solo dispositivo conectado:

```powershell
adb reboot bootloader
fastboot devices
fastboot getvar product
fastboot getvar is-userspace
fastboot getvar unlocked
fastboot flashing get_unlock_ability
```

Se detectó producto `k79v1_64`, `is-userspace: no`, `unlocked: no` y `unlock_ability = 16777216` (`0x01000000`). Este fue el valor observado, no el `1` usual documentado; no se interpretó por sí solo como prueba de desbloqueo. El comando siguiente y las verificaciones posteriores confirmaron el resultado.

```powershell
fastboot flashing unlock
```

Leer y completar cualquier confirmación en la pantalla del teléfono según sus instrucciones. El procedimiento puede borrar datos. Esperar a que termine: en el caso probado devolvió OKAY en aproximadamente 19 segundos.

```powershell
fastboot getvar unlocked
fastboot getvar secure
fastboot reboot
```

Resultados: `unlocked: yes`, `secure: no`. Después del reinicio apareció Orange State. Dejar terminar el arranque o restablecimiento; completar la configuración y volver a habilitar/autorizar ADB si se solicita.

## 9. Verificación final en Android

```powershell
adb shell getprop ro.product.model
adb shell getprop ro.build.display.id
adb shell getprop sys.boot_completed
adb shell getprop ro.boot.flash.locked
adb shell getprop ro.boot.verifiedbootstate
adb shell getprop ro.boot.vbmeta.device_state
adb shell getprop sys.oem_unlock_allowed
```

El caso exitoso devolvió `CPH2205`, `CPH2205_11_F.72`, `1`, `0`, `orange`, `unlocked`, `1`. El arranque posterior al desbloqueo conservó el estado. No se probó la persistencia frente a OTA, restauración de firmware o cambios posteriores.

Si no se obtiene ese resultado, informar el firmware exacto y las propiedades no identificadoras. No publicar respaldos, números de serie, IMEI, claves ni logs completos. Conservar las pruebas privadas y consultar [recuperación](RECOVERY.md).
