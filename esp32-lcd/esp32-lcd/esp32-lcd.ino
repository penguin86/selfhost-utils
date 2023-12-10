#include <WiFi.h>
#include <WiFiClient.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <LiquidCrystal.h>
#include "config.h"

// ------- Configuration is in config.h file -------

const int WEBSERVER_PORT = 80;
const char* WEBSERVER_MESSAGE_PARAM = "message";

/*
 
LCD Pin –>ESP32 Pins

    PIN01-VSS -> GND
    PIN02-VDD -> 5V
    PIN03 V0-> 10K Pot (Middle pin)
    PIN04 RS->  GPIO19
    PIN05 RW-> GND
    PIN06  E  ->  GPIO23
    PIN07 D0-> NOT USED
    PIN08 D1-> NOT USED
    PIN09 D2-> NOT USED
    PIN10 D3-> NOT USED
    PIN11 D4->  GPIO18
    PIN12 D5->  GPIO17
    PIN13 D6->  GPIO16
    PIN14 D7->  GPIO15
    PIN15 A-> 5V
    PIN16 K-> GND

 */

WebServer server(WEBSERVER_PORT); // Server on port 80
LiquidCrystal lcd(19, 23, 18, 17, 16, 15);
const int led = 13;

void lcdPrintMultilineMessage(String message) {
  lcd.clear();
  int startFrom = 0;
  for (int i=0; i<DISPLAY_HEIGHT; i++) {
    lcd.setCursor(0,i);
    lcd.print(
      message.substring(startFrom, startFrom + DISPLAY_WIDTH)
    );
    startFrom += DISPLAY_WIDTH;
  }
}

void handleRoot() {
  digitalWrite(led, 1);
  lcdPrintMultilineMessage(server.arg(WEBSERVER_MESSAGE_PARAM));
  server.send(200, "text/plain", "ok");
  digitalWrite(led, 0);
}

void handleNotFound() {
  digitalWrite(led, 1);
  String message = "File Not Found\n\n";
  message += "URI: ";
  message += server.uri();
  message += "\nMethod: ";
  message += (server.method() == HTTP_GET) ? "GET" : "POST";
  message += "\nArguments: ";
  message += server.args();
  message += "\n";
  for (uint8_t i = 0; i < server.args(); i++) {
    message += " " + server.argName(i) + ": " + server.arg(i) + "\n";
  }
  server.send(404, "text/plain", message);
  digitalWrite(led, 0);
}

void setup(void) {
  // LCD: set up
  lcd.begin(DISPLAY_WIDTH, DISPLAY_HEIGHT);

  // SERIAL: set up
  Serial.begin(115200);
  Serial.println("");

  // STATUS LED: set up
  pinMode(led, OUTPUT);
  digitalWrite(led, 0);
  
  // LCD: Show SSID
  lcd.print("Conn to wifi...");
  lcd.setCursor(0,1);
  lcd.print(WIFI_SSID);

  // Connect to wifi
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  // Wait for connection
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Connected to ");
  Serial.println(WIFI_SSID);
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  // Print IP addr to LCD
  lcd.clear();
  lcd.print("Connected! IP:");
  lcd.setCursor(0,1);
  lcd.print(WiFi.localIP());

  if (MDNS.begin("esp32")) {
    Serial.println("MDNS responder started");
  }

  server.on("/", handleRoot);
  server.onNotFound(handleNotFound);

  server.begin();
  Serial.println("HTTP server started");

}

void loop(void) {
  server.handleClient();
  delay(2);//allow the cpu to switch to other tasks
}
