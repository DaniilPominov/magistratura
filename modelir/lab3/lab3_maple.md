# Лабораторная работа 3. Бифуркация Андронова–Хопфа

Система Ван дер Поля:

\[
x' = y,\qquad y' = (\lambda - x^2)y - x
\]

Бифуркация происходит при \(\lambda = 0\): при \(\lambda<0\) начало координат устойчиво, при \(\lambda>0\) оно теряет устойчивость и рождается устойчивый предельный цикл.

```maple
restart;
with(DEtools):

sys := [diff(x(t), t) = y(t), diff(y(t), t) = (lambda - x(t)^2)*y(t) - x(t)]:

ic := [[x(0) = 0.1, y(0) = 0], [x(0) = 2, y(0) = 0], [x(0) = 0, y(0) = 2],
       [x(0) = -2, y(0) = 0], [x(0) = 0, y(0) = -2]]:

pp := L -> phaseportrait(eval(sys, lambda = L), [x(t), y(t)], t = 0 .. 50, ic,
        x = -3 .. 3, y = -3 .. 3, stepsize = 0.02, arrows = medium,
        linecolor = [red, blue, green, black, magenta],
        title = cat("lambda = ", convert(L, string))):

LinearAlgebra:-Eigenvalues(Matrix([[0, 1], [-1, lambda]]));

pp(-1);   # до бифуркации
pp(0);    # бифуркационное значение
pp(1);    # после бифуркации
```
