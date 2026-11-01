# Лабораторная работа 4. Странные аттракторы, синхронизация хаоса

Вариант 11: \(x_{n+1}=r\tan(x_n)\), \(r=0.6;\ 0.8\).

```maple
restart;
with(plots):
with(DEtools):

# 1. Аттрактор Лоренца и два близких решения
sigma_ := 10: r := 28: b := 8/3:

lor := [diff(x(t), t) = sigma_*(y(t) - x(t)),
        diff(y(t), t) = r*x(t) - y(t) - x(t)*z(t),
        diff(z(t), t) = x(t)*y(t) - b*z(t)]:

s1 := dsolve([op(lor), x(0) = 0.5, y(0) = 1, z(0) = 1.5],
             [x(t), y(t), z(t)], numeric, method = dverk78):
s2 := dsolve([op(lor), x(0) = 0.5 + 1e-8, y(0) = 1, z(0) = 1.5],
             [x(t), y(t), z(t)], numeric, method = dverk78):

p1 := odeplot(s1, [x(t), y(t), z(t)], 0 .. 35, numpoints = 10000, color = red):
p2 := odeplot(s2, [x(t), y(t), z(t)], 0 .. 35, numpoints = 10000, color = blue):
display(p1, p2, axes = boxed, labels = [x, y, z],
        legend = ["IC 1", "IC 2"],
        title = "Lorenz attractor: two close initial conditions");

q1 := odeplot(s1, [t, x(t)], 0 .. 35, numpoints = 4000, color = red):
q2 := odeplot(s2, [t, x(t)], 0 .. 35, numpoints = 4000, color = blue):
display(q1, q2, labels = [t, x], legend = ["IC 1", "IC 2"],
        title = "Time series x(t): two close initial conditions");

# 2. Синхронизация передатчика и приемника
tr := [diff(u(t), t) = sigma_*(v(t) - u(t)),
       diff(v(t), t) = r*u(t) - v(t) - 20*u(t)*w(t),
       diff(w(t), t) = 5*u(t)*v(t) - b*w(t)]:

ics := [u(0) = 0.1, v(0) = 0.1, w(0) = 0.1,
        ur(0) = 0.5, vr(0) = 0.5, wr(0) = 0.5]:

# 2a. Без маскирования
rec0 := [diff(ur(t), t) = sigma_*(vr(t) - ur(t)),
         diff(vr(t), t) = r*u(t) - vr(t) - 20*u(t)*wr(t),
         diff(wr(t), t) = 5*u(t)*vr(t) - b*wr(t)]:

sol0 := dsolve([op(tr), op(rec0), op(ics)],
               [u(t), v(t), w(t), ur(t), vr(t), wr(t)],
               numeric, method = dverk78):

odeplot(sol0, [[t, u(t)], [t, ur(t)]], 0 .. 40, numpoints = 4000,
        color = [red, blue], legend = ["u", "u_r"], labels = [t, "u"],
        title = "Synchronization without masking: u and u_r");
odeplot(sol0, [[t, v(t)], [t, vr(t)]], 0 .. 40, numpoints = 4000,
        color = [red, blue], legend = ["v", "v_r"], labels = [t, "v"],
        title = "Synchronization without masking: v and v_r");
odeplot(sol0, [[t, w(t)], [t, wr(t)]], 0 .. 40, numpoints = 4000,
        color = [red, blue], legend = ["w", "w_r"], labels = [t, "w"],
        title = "Synchronization without masking: w and w_r");

# 2b. Маскирование полезным сигналом
eps := 0.01:
mask := u(t) + eps*sin(t):

rec1 := [diff(ur(t), t) = sigma_*(vr(t) - ur(t)),
         diff(vr(t), t) = r*mask - vr(t) - 20*mask*wr(t),
         diff(wr(t), t) = 5*mask*vr(t) - b*wr(t)]:

sol1 := dsolve([op(tr), op(rec1), op(ics)],
               [u(t), v(t), w(t), ur(t), vr(t), wr(t)],
               numeric, method = dverk78):

odeplot(sol1, [[t, u(t) + eps*sin(t)], [t, ur(t)]], 0 .. 40,
        numpoints = 4000, color = [red, blue],
        legend = ["u + s", "u_r"], labels = [t, "signal"],
        title = "Masked signal u + 0.01 sin(t) and receiver u_r");

odeplot(sol1, [t, u(t) + eps*sin(t) - ur(t)], 15 .. 40,
        numpoints = 4000, color = black, labels = [t, "u + s - u_r"],
        title = "Recovered useful signal: u + s - u_r");

# 3. Вариант 11: итерационная диаграмма x_{n+1} = r*tan(x_n)
cobweb := proc(rr, x0, N, a, b)
  local f, P, i, s, yn;
  f := x -> rr*tan(x);
  s := evalf(x0);
  P := [[s, s]];
  for i to N do
    yn := evalf(f(s));
    P := [op(P), [s, yn], [yn, yn]];
    s := yn;
  end do;
  display(
    plot([f(x), x], x = a .. b, color = [red, blue],
         thickness = 2, legend = ["f(x)", "y = x"]),
    pointplot(P, connect = true, color = green, thickness = 2,
              symbol = solidcircle, symbolsize = 4),
    view = [a .. b, a .. b], axes = boxed,
    labels = ["x_n", "x_{n+1}"],
    title = cat("Cobweb diagram: r = ", convert(rr, string))
  );
end proc:

cobweb(0.6, 0.5, 30, -1.5, 1.5);
cobweb(0.8, 0.5, 30, -1.5, 1.5);
```
