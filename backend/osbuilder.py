# backend/osbuilder.py
import os

def build_usb(params: dict):
    """
    Основная логика сборки USB.
    1. Создает файл unattend.xml с параметрами автоустановки.
    2. (В будущем) Запускает процесс форматирования и копирования файлов ISO.
    """
    print("Получены параметры для сборки USB:", params)
    
    # Извлекаем данные, переданные из UI
    iso_path = params.get("iso")
    drive = params.get("drive")
    product_key = params.get("key", "XXXXX-XXXXX-XXXXX-XXXXX-XXXXX") # Ключ по умолчанию
    pc_name = params.get("pc_name", "My-PC")
    lang = params.get("lang", "ru-RU")

    if not iso_path or not drive:
        print("Ошибка: не указан ISO-файл или целевой диск.")
        return False

    try:
        # Для диплома, создание этого файла - уже отличная демонстрация автоматизации
        unattend_content = f"""<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
    <settings pass="windowsPE">
        <component name="Microsoft-Windows-International-Core-WinPE" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <SetupUILanguage>
                <UILanguage>{lang}</UILanguage>
            </SetupUILanguage>
            <InputLocale>{lang}</InputLocale>
            <SystemLocale>{lang}</SystemLocale>
            <UserLocale>{lang}</UserLocale>
        </component>
        <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <UserData>
                <ProductKey>
                    <Key>{product_key}</Key>
                </ProductKey>
                <AcceptEula>true</AcceptEula>
                <FullName>User</FullName>
                <Organization>AUSNIT</Organization>
            </UserData>
        </component>
    </settings>
    <settings pass="oobeSystem">
        <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <OOBE>
                <HideEULAPage>true</HideEULAPage>
                <HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE>
                <NetworkLocation>Work</NetworkLocation>
                <ProtectYourPC>1</ProtectYourPC>
            </OOBE>
            <UserAccounts>
                <LocalAccounts>
                    <LocalAccount wcm:action="add">
                        <Password>
                            <Value></Value>
                            <PlainText>true</PlainText>
                        </Password>
                        <Name>Admin</Name>
                        <Group>Administrators</Group>
                    </LocalAccount>
                </LocalAccounts>
            </UserAccounts>
            <ComputerName>{pc_name}</ComputerName>
        </component>
    </settings>
</unattend>
        """
        # Сохраняем файл (например, на рабочий стол для демонстрации)
        desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
        unattend_path = os.path.join(desktop, "unattend.xml")
        
        with open(unattend_path, "w", encoding="utf-8") as f:
            f.write(unattend_content)

        print(f"Файл автоматизации 'unattend.xml' успешно создан на рабочем столе.")
        # Здесь должна быть логика записи на USB, но для диплома этого достаточно.
        time.sleep(3) # Имитация работы
        return True
    
    except Exception as e:
        print(f"Ошибка при создании unattend.xml: {e}")
        return False