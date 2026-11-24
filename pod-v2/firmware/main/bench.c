#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define RELAY GPIO_NUM_3
static const gpio_num_t led[] = {GPIO_NUM_0, GPIO_NUM_1, GPIO_NUM_10};

static void reply(const char *message)
{
    ESP_ERROR_CHECK(uart_write_bytes(UART_NUM_0, message, strlen(message)) < 0 ? ESP_FAIL : ESP_OK);
}

// Drain the scanner independently. Only the byte count reaches the console.
static uint32_t received;
static portMUX_TYPE count_lock = portMUX_INITIALIZER_UNLOCKED;
static void read_scanner(void *unused)
{
    uint8_t buffer[128];
    for (;;) {
        int n = uart_read_bytes(UART_NUM_1, buffer, sizeof(buffer), portMAX_DELAY);
        ESP_ERROR_CHECK(n < 0 ? ESP_FAIL : ESP_OK);
        portENTER_CRITICAL(&count_lock);
        received += n;
        portEXIT_CRITICAL(&count_lock);
    }
}

static void scan_wifi(void)
{
    static bool initialized;
    if (!initialized) {
        ESP_ERROR_CHECK(esp_netif_init());
        ESP_ERROR_CHECK(esp_event_loop_create_default());
        wifi_init_config_t config = WIFI_INIT_CONFIG_DEFAULT();
        config.nvs_enable = false;
        ESP_ERROR_CHECK(esp_wifi_init(&config));
        ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
        ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
        ESP_ERROR_CHECK(esp_wifi_start());
        initialized = true;
    }
    wifi_scan_config_t scan = {.scan_type = WIFI_SCAN_TYPE_PASSIVE};
    ESP_ERROR_CHECK(esp_wifi_scan_start(&scan, true));
    uint16_t count;
    ESP_ERROR_CHECK(esp_wifi_scan_get_ap_num(&count));
    ESP_ERROR_CHECK(esp_wifi_clear_ap_list());
    char line[48];
    snprintf(line, sizeof(line), "Access points: %u\r\n", (unsigned)count);
    reply(line);
}

static void command(const char *line)
{
    const char *colors[] = {"red", "green", "blue", "off"};
    for (int c = 0; c < 4; c++) {
        if (strcmp(line, colors[c]) == 0) {
            for (int i = 0; i < 3; i++)
                ESP_ERROR_CHECK(gpio_set_level(led[i], i == c));
            reply("OK\r\n");
            return;
        }
    }
    if (strcmp(line, "pulse relay") == 0) {
        ESP_ERROR_CHECK(gpio_set_level(RELAY, 1));
        vTaskDelay(pdMS_TO_TICKS(4000));
        ESP_ERROR_CHECK(gpio_set_level(RELAY, 0));
        reply("Relay off\r\n");
    } else if (strcmp(line, "scanner") == 0) {
        portENTER_CRITICAL(&count_lock);
        uint32_t count = received;
        portEXIT_CRITICAL(&count_lock);
        char result[48];
        snprintf(result, sizeof(result), "Scanner bytes: %lu\r\n", (unsigned long)count);
        reply(result);
    } else if (strcmp(line, "wifi") == 0) {
        scan_wifi();
    } else {
        reply("Commands: red green blue off scanner wifi | pulse relay\r\n");
    }
}

void app_main(void)
{
    ESP_ERROR_CHECK(gpio_set_level(RELAY, 0));
    gpio_config_t pins = {
        .pin_bit_mask = (1ULL << RELAY) | (1ULL << led[0]) |
                        (1ULL << led[1]) | (1ULL << led[2]),
        .mode = GPIO_MODE_OUTPUT,
    };
    ESP_ERROR_CHECK(gpio_config(&pins));
    uart_config_t uart = {
        .baud_rate = 9600, .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE, .stop_bits = UART_STOP_BITS_1,
        .source_clk = UART_SCLK_DEFAULT,
    };
    ESP_ERROR_CHECK(uart_param_config(UART_NUM_1, &uart));
    ESP_ERROR_CHECK(uart_set_pin(UART_NUM_1, 4, 5, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    ESP_ERROR_CHECK(uart_driver_install(UART_NUM_1, 2048, 0, 0, NULL, 0));
    ESP_ERROR_CHECK(xTaskCreate(read_scanner, "scanner", 2048, NULL, 4, NULL)
                    == pdPASS ? ESP_OK : ESP_ERR_NO_MEM);
    uart.baud_rate = 115200;
    ESP_ERROR_CHECK(uart_param_config(UART_NUM_0, &uart));
    ESP_ERROR_CHECK(uart_driver_install(UART_NUM_0, 512, 0, 0, NULL, 0));
    char line[32];
    size_t used = 0;
    bool invalid = false;
    for (;;) {
        unsigned char ch;
        int count = uart_read_bytes(UART_NUM_0, &ch, 1, portMAX_DELAY);
        ESP_ERROR_CHECK(count < 0 ? ESP_FAIL : ESP_OK);
        if (count == 0)
            continue;
        if (ch == '\r' || ch == '\n') {
            if (invalid)
                reply("Invalid command\r\n");
            else if (used) {
                line[used] = 0;
                command(line);
            }
            used = 0;
            invalid = false;
        } else if (used == sizeof(line) - 1 || ch < 32 || ch > 126) {
            invalid = true;
        } else {
            line[used++] = ch;
        }
    }
}
