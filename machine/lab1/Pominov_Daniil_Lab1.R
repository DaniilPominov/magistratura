sink("Pominov_Daniil_Lab1.txt")

# 1
num <- 1:42
#записываем строки таблицы
hard <- c(1.13, 1.17, 1.20, 1.17, 1.18, 1.23, 1.21, 1.22,
          1.14, 1.14, 1.14, 1.18, 1.13, 1.06, 1.26)

neutral <- c(1.48, 1.54, 1.47, 1.45, 1.46, 1.55, 1.45, 1.44,
             1.53, 1.46, 1.53, 1.53, 1.53, 1.51)

soft <- c(1.49, 1.50, 1.53, 1.54, 1.52, 1.49, 1.49, 1.51,
          1.54, 1.60, 1.50, 1.53, 1.53)

a <- c(hard, neutral, soft)
#факторные переменные
b <- c(rep("жесткая", length(hard)),
       rep("ph нейтральная", length(neutral)),
       rep("мягкая", length(soft)))

b_factor <- factor(b)

print("Вектор num:")
print(num)
print("Вектор a:")
print(a)
print("Вектор b:")
print(b)
print("Фактор b_factor:")
print(b_factor)
# 2
my_frame <- data.frame(ID = num, Value = a, WaterType = b_factor)

print("Содержимое my_frame:")
print(my_frame)

print("Размерность my_frame:")
print(dim(my_frame))

print("Структура my_frame:")
str(my_frame)

print("Названия столбцов:")
print(names(my_frame))

print("Первые 4 строки:")
print(head(my_frame, 4))

print("Объекты с Value от 1.20 до 1.50:")
print(my_frame[my_frame$Value >= 1.20 & my_frame$Value <= 1.50, ])

print("Объекты с жёсткой водой:")
print(my_frame[my_frame$WaterType == "жесткая", ])

print("Объекты с ID 1, 3, 6, 9, 10:")
print(my_frame[my_frame$ID %in% c(1, 3, 6, 9, 10), ])

print("Объект с минимальным значением Value:")
print(my_frame[which.min(my_frame$Value), ])

# 3
#новая запись для my_frame
new_row <- data.frame(
  ID = 43,
  Value = 1.55,
  WaterType = factor("мягкая", levels = levels(my_frame$WaterType))
)

my_frame <- rbind(my_frame, new_row)

mean_val <- mean(my_frame$Value)
sd_val <- sd(my_frame$Value)

print(paste("mean =", mean_val))
print(paste("sd =", sd_val))

set.seed(123)
New <- rnorm(nrow(my_frame), mean = mean_val, sd = sd_val)

my_frame <- cbind(my_frame, New)

print("Обновлённая таблица my_frame:")
print(my_frame)

# 4-6
#считываем файл
flat <- openxlsx::read.xlsx(xlsxFile = "Flat98.xlsx", sheet = "Data")

print("Первые 5 строк таблицы flat:")
print(head(flat, 5))

f <- function(x) {
  return(order(x)[1:6])
}

indices_dist <- f(flat$dist)
print("Шесть самых близких к центру квартир (по dist):")
print(flat[indices_dist, ])

# Применяем f к price среди квартир с телефоном
flat_with_tel <- flat[flat$tel == 1, ]
indices_price <- f(flat_with_tel$price)
print("Шесть самых дешёвых квартир с телефоном:")
print(flat_with_tel[indices_price, ])

sink()