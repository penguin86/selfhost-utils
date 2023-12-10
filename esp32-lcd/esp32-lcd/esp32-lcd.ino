#include <WiFi.h>
#include <WiFiClient.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <LiquidCrystal.h>

const char* ssid = "ichibi";
const char* password = "uffobaruffo";

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

WebServer server(80);

// Init lcd
LiquidCrystal lcd(19, 23, 18, 17, 16, 15);

const int led = 13;

void handleRoot() {
  digitalWrite(led, 1);
  lcd.clear();
  for (uint8_t i = 0; i < server.args(); i++) {
    lcd.print(server.arg(i));
  }
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
  // set up the LCD's number of columns and rows:
  lcd.begin(16, 2);
  // Print a message to the LCD.
  lcd.print("Connecting to wifi...");

  // Init
  pinMode(led, OUTPUT);
  digitalWrite(led, 0);
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.println("");

  // Wait for connection
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Connected to ");
  Serial.println(ssid);
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  // Print to LCD
  lcd.clear();
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



  
  // set the cursor to column 0, line 1
  // (note: line 1 is the second row, since counting begins with 0):
  lcd.setCursor(0, 1);
  // print the number of seconds since reset:
  lcd.print(millis() / 1000);
}
