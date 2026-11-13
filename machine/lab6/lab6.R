# Загрузка данных
data <- read.csv("ford.csv", stringsAsFactors = TRUE)

# Удаление строк с пропущенными значениями (если есть)
data <- na.omit(data)

# Структура данных
str(data)

normalize <- function(x) {
  (x - mean(x)) / sd(x)
}

# Числовые предикторы
numeric_cols <- c("year", "mileage", "tax", "mpg", "engineSize")
# Категориальные предикторы
categorical_cols <- c("model", "transmission", "fuelType")
#Label Encoding, нормировка
data_model <- data
data_model[numeric_cols] <- lapply(data_model[numeric_cols], normalize)
data_model[categorical_cols] <- lapply(data_model[categorical_cols], as.numeric)

model <- lm(price ~ ., data = data_model)
#2
library(caret)
dummy <- dummyVars(~ model + transmission + fuelType, data = data)
data_ohe <- data.frame(predict(dummy, newdata = data))
data_ohe <- cbind(data[, c("year", "mileage", "tax", "mpg", "engineSize", "price")], data_ohe)
data_ohe[numeric_cols] <- lapply(data_ohe[numeric_cols], normalize)

model_O_H_encoded <- lm(price ~ ., data = data_ohe)
#3
data_ohe_log <- data_ohe
data_ohe_log$price <- log(data_ohe_log$price)
model_log_response <- lm(price ~ ., data = data_ohe_log)
#4
data_ohe_sqrt <- data_ohe
data_ohe_sqrt$price <- sqrt(data_ohe_sqrt$price)
model_sqrt_response <- lm(price ~ ., data = data_ohe_sqrt)
#5
data_ohe_trans <- data_ohe
data_ohe_trans$log_mileage <- normalize(log(data$mileage + 1))
model_transformed_feature <- lm(price ~ ., data = data_ohe_trans)
#6
data_ohe_trans_log <- data_ohe_trans
data_ohe_trans_log$price <- log(data_ohe_trans_log$price)
model_log_response_transformed_feature <- lm(price ~ ., data = data_ohe_trans_log)

summary(model)
summary(model_O_H_encoded)
summary(model_log_response)
summary(model_sqrt_response)
summary(model_transformed_feature)
summary(model_log_response_transformed_feature)

# Визуальная проверка допущений
par(mfrow = c(2, 2))
plot(model_O_H_encoded)


# --- 1. Новый объект с уровнями факторов, как в обучающей выборке ---
new_car <- data.frame(
  model        = factor("Focus", levels = levels(data$model)),
  transmission = factor("Manual", levels = levels(data$transmission)),
  fuelType     = factor("Petrol", levels = levels(data$fuelType)),
  year         = 2019,
  mileage      = 15000,
  tax          = 145,
  mpg          = 60.1,
  engineSize   = 1.0
)

# --- 2. Нормировка числовых предикторов по параметрам обучения ---
new_car$year       <- (new_car$year       - mean(data$year))       / sd(data$year)
new_car$mileage    <- (new_car$mileage    - mean(data$mileage))    / sd(data$mileage)
new_car$tax        <- (new_car$tax        - mean(data$tax))        / sd(data$tax)
new_car$mpg        <- (new_car$mpg        - mean(data$mpg))        / sd(data$mpg)
new_car$engineSize <- (new_car$engineSize - mean(data$engineSize)) / sd(data$engineSize)

# --- 3. log_mileage (ВАЖНО: считаем от ИСХОДНОГО пробега 15000) ---
new_car$log_mileage <- (log(15000 + 1) - mean(log(data$mileage + 1))) /
  sd(log(data$mileage + 1))

# --- 4. One Hot Encoding ---
# check.names = FALSE — чтобы имена колонок совпали с обучающими
new_car_ohe <- as.data.frame(predict(dummy, newdata = new_car),
                             check.names = FALSE)

# --- 5. Собираем финальный data.frame ---
new_car_final <- new_car[, numeric_cols]          # year, mileage, tax, mpg, engineSize
new_car_final$log_mileage <- new_car$log_mileage
new_car_final <- cbind(new_car_final, new_car_ohe)

# --- 6. Приводим порядок и состав колонок к обучающим ---
train_cols <- setdiff(names(data_ohe_trans_log), "price")

missing_cols <- setdiff(train_cols, names(new_car_final))
extra_cols   <- setdiff(names(new_car_final), train_cols)
cat("Отсутствуют в newdata:", if (length(missing_cols)) missing_cols else "нет", "\n")
cat("Лишние в newdata:",      if (length(extra_cols))   extra_cols   else "нет", "\n")

# Добавляем недостающие OHE-колонки нулями
for (col in missing_cols) new_car_final[[col]] <- 0

# Выставляем точный порядок
new_car_final <- new_car_final[, train_cols, drop = FALSE]

# --- 7. Прогноз ---
pred_log   <- predict(model_log_response_transformed_feature, newdata = new_car_final)
pred_price <- exp(pred_log)
cat("Прогнозируемая цена:", round(pred_price, 2), "руб.\n")