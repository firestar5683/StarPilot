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
void car_err_fun(double *nom_x, double *delta_x, double *out_6338568395475486083);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_5410100343915451790);
void car_H_mod_fun(double *state, double *out_823602999692946123);
void car_f_fun(double *state, double dt, double *out_5252072111533144957);
void car_F_fun(double *state, double dt, double *out_5472890640690018040);
void car_h_25(double *state, double *unused, double *out_8566352363547608598);
void car_H_25(double *state, double *unused, double *out_5673419960197083828);
void car_h_24(double *state, double *unused, double *out_1105741821560728000);
void car_H_24(double *state, double *unused, double *out_5330649520523751468);
void car_h_30(double *state, double *unused, double *out_2652619336876860225);
void car_H_30(double *state, double *unused, double *out_8245627783384859590);
void car_h_26(double *state, double *unused, double *out_1745332744404768787);
void car_H_26(double *state, double *unused, double *out_9031820794638411564);
void car_h_27(double *state, double *unused, double *out_4878718442501097373);
void car_H_27(double *state, double *unused, double *out_7977522219140748809);
void car_h_29(double *state, double *unused, double *out_1709109483975197790);
void car_H_29(double *state, double *unused, double *out_8755859127699251774);
void car_h_28(double *state, double *unused, double *out_2770626730810236969);
void car_H_28(double *state, double *unused, double *out_3673460110629721200);
void car_h_31(double *state, double *unused, double *out_4928902835293586248);
void car_H_31(double *state, double *unused, double *out_5642773998320123400);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}