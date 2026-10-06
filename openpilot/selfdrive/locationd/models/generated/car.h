#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_4652830232542905037);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3291886134262608133);
void car_H_mod_fun(double *state, double *out_4576150220690732126);
void car_f_fun(double *state, double dt, double *out_829378765985642412);
void car_F_fun(double *state, double dt, double *out_5290468730257954652);
void car_h_25(double *state, double *unused, double *out_1533454437622332874);
void car_H_25(double *state, double *unused, double *out_327541604493932714);
void car_h_24(double *state, double *unused, double *out_5835817958400148077);
void car_H_24(double *state, double *unused, double *out_1401321514683381355);
void car_h_30(double *state, double *unused, double *out_5170903965876355224);
void car_H_30(double *state, double *unused, double *out_7244231945985549469);
void car_h_26(double *state, double *unused, double *out_471825905204601611);
void car_H_26(double *state, double *unused, double *out_3413961714380123510);
void car_h_27(double *state, double *unused, double *out_8313805285979098383);
void car_H_27(double *state, double *unused, double *out_5069468634185124558);
void car_h_29(double *state, double *unused, double *out_8274166840172350747);
void car_H_29(double *state, double *unused, double *out_3356105907315573525);
void car_h_28(double *state, double *unused, double *out_2446841466723662246);
void car_H_28(double *state, double *unused, double *out_1726293109753957049);
void car_h_31(double *state, double *unused, double *out_1259737292248810794);
void car_H_31(double *state, double *unused, double *out_358187566370893142);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}