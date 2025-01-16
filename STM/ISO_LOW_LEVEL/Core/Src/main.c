#include "main.h"
#include "tim.h"
#include "usart.h"
#include "gpio.h"
#include <stdio.h>
#include <string.h>

/* Private variables ---------------------------------------------------------*/
char uart_buf[50];  // Buffer for UART messages
float voltage_response;

/* Function Prototypes -------------------------------------------------------*/
void SystemClock_Config(void);
float calculate_voltage(uint32_t pwm_duty_cycle, uint32_t pwm_frequency);

int main(void)
{
    HAL_Init(); // Initialize the HAL Library
    SystemClock_Config(); // Configure the system clock

    MX_GPIO_Init(); // Initialize GPIO
    MX_USART2_UART_Init(); // Initialize USART
    MX_TIM2_Init(); // Initialize Timer 2 (for PWM input capture)

    HAL_TIM_IC_Start(&htim2, TIM_CHANNEL_1); // Start input capture on TIM2 CH1

    uint32_t pwm_duty_cycle;
    uint32_t pwm_frequency;

    while (1)
    {
        /* Read PWM Duty Cycle and Frequency */
        uint32_t pulse_width = HAL_TIM_ReadCapturedValue(&htim2, TIM_CHANNEL_1);
        uint32_t period = __HAL_TIM_GET_AUTORELOAD(&htim2);

        if (period > 0)
        {
            pwm_duty_cycle = (pulse_width * 100) / period;  // Duty cycle as a percentage
            pwm_frequency = HAL_RCC_GetHCLKFreq() / ((period + 1) * (htim2.Instance->PSC + 1));
        }
        else
        {
            pwm_duty_cycle = 0;
            pwm_frequency = 0;
        }

        /* Voltage Calculation */
        voltage_response = calculate_voltage(pwm_duty_cycle, pwm_frequency);

        /* Format and Send Data over UART */
        sprintf(uart_buf, sizeof(uart_buf), "Duty: %lu%%, Freq: %lu Hz, Voltage: %.2fV\r\n",pwm_duty_cycle, pwm_frequency, voltage_response);
        HAL_UART_Transmit(&huart2, (uint8_t*)uart_buf, strlen(uart_buf), HAL_MAX_DELAY);

        HAL_Delay(1000);  // Transmit every second
    }
}

/* Voltage Calculation Based on Duty Cycle */
float calculate_voltage(uint32_t pwm_duty_cycle, uint32_t pwm_frequency)
{
    if (pwm_frequency == 1000)  // Only at 1 kHz frequency
    {
        switch (pwm_duty_cycle)
        {
            case 100: return 0.0;   // Standby/Vehicle detection
            case 10:  return 2.7;   // Cable plugged
            case 50:  return 7.0;   // Normal charging
            case 95:  return 12.0;  // Charging complete
            case 5:   return 0.0;   // Fault state
            case 20:  return 3.6;   // Ready to charge
            case 30:  return 5.5;   // Renewable energy charging
            default:  return 2.7;   // Default case for unrecognized duty cycle
        }
    }
    return 2.7;  // Default voltage for other frequencies
}

/* System Clock Configuration */
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    /** Configure the main internal regulator output voltage
    */
    __HAL_RCC_PWR_CLK_ENABLE();
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE3);

    /** Initializes the RCC Oscillators according to the specified parameters
    * in the RCC_OscInitTypeDef structure.
    */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    RCC_OscInitStruct.HSIState = RCC_HSI_ON;
    RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
    RCC_OscInitStruct.PLL.PLLM = 16;
    RCC_OscInitStruct.PLL.PLLN = 336;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV4;
    RCC_OscInitStruct.PLL.PLLQ = 2;
    RCC_OscInitStruct.PLL.PLLR = 2;

    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
    {
        Error_Handler();
    }

    /** Initializes the CPU, AHB and APB buses clocks
    */
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                                   RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
    {
        Error_Handler();
    }
}

/* Error Handler */
void Error_Handler(void)
{
    /* USER CODE BEGIN Error_Handler_Debug */
    /* User can add his own implementation to report the HAL error return state */
    __disable_irq();
    while (1)
    {
    }
    /* USER CODE END Error_Handler_Debug */
}
