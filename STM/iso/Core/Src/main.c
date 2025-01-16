/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "tim.h"
#include "usart.h"
#include "gpio.h"
#include <stdio.h>
#include <string.h>
/* Private variables ---------------------------------------------------------*/
char uart_buffer[50];
uint32_t pwm_duty_cycle=10;
uint32_t pwm_frequency=1000;
float voltage_response;

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
void send_uart_response(float voltage);
float calculate_voltage(uint32_t duty_cycle);

/* Main Program */
int main(void)
{
    /* Initialize all configured peripherals */
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART2_UART_Init();   // UART for sending responses
    MX_TIM2_Init();          // Timer for PWM Input Capture

    /* Start PWM input capture */
    HAL_TIM_IC_Start(&htim2, TIM_CHANNEL_1);

    /* Infinite loop */
    while (1)
    {
        /* Get the PWM duty cycle */
//        pwm_duty_cycle = __HAL_TIM_GET_COMPARE(&htim2, TIM_CHANNEL_1);
//        pwm_frequency = 1000//HAL_RCC_GetHCLKFreq() / (__HAL_TIM_GET_AUTORELOAD(&htim2) + 1);

        /* Calculate the corresponding voltage based on the duty cycle */
        voltage_response = calculate_voltage(pwm_duty_cycle);

        /* Send the calculated voltage via UART */
        send_uart_response(voltage_response);

        /* Delay between transmissions */
        HAL_Delay(1000);  // Delay 1 second before next response
    }
}

/* Function to calculate voltage based on duty cycle */
float calculate_voltage(uint32_t duty_cycle)
{
    if (duty_cycle == 100) {
        return 0.0;  // Standby/Vehicle Detection
    } else if (duty_cycle == 10) {
        return 2.7;  // Cable plugged in
    } else if (duty_cycle == 50) {
        return 7.0;  // Charging state
    } else if (duty_cycle == 95) {
        return 12.0;  // Charging complete
    } else if (duty_cycle == 5) {
        return 0.0;  // Fault state
    } else if (duty_cycle == 20) {
        return 3.6;  // Ready to charge
    } else if (duty_cycle == 30) {
        return 5.5;  // Charging with renewable energy
    }
    return 0.0;  // Default or unknown state
}

/* Function to send voltage response via UART */
void send_uart_response(float voltage)
{
	sprintf(uart_buffer, sizeof(uart_buffer), "Duty: %lu%%, Freq: %lu Hz, Voltage: %.2fV\r\n",pwm_duty_cycle, pwm_frequency, voltage_response);
    HAL_UART_Transmit(&huart2, (uint8_t *)uart_buffer, strlen(uart_buffer), HAL_MAX_DELAY);
}




/* System Clock Configuration ------------------------------------------------*/
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    RCC_OscInitStruct.HSIState = RCC_HSI_ON;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
    RCC_OscInitStruct.PLL.PLLM = 16;
    RCC_OscInitStruct.PLL.PLLN = 336;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV4;
    RCC_OscInitStruct.PLL.PLLQ = 2;
    RCC_OscInitStruct.PLL.PLLR = 2;
    HAL_RCC_OscConfig(&RCC_OscInitStruct);

    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;
    HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2);
}

/* UART Initialization -------------------------------------------------------*/


/* Error Handler --------------------------------------------------------------*/
void Error_Handler(void)
{
    while (1)
    {
        // Error handling code
    }
}
