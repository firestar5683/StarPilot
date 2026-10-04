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
void car_err_fun(double *nom_x, double *delta_x, double *out_8303558303892577205);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_1062916904929925329);
void car_H_mod_fun(double *state, double *out_3641608302244706687);
void car_f_fun(double *state, double dt, double *out_8905281951230386628);
void car_F_fun(double *state, double dt, double *out_3707619108862692258);
void car_h_25(double *state, double *unused, double *out_8179086173107337673);
void car_H_25(double *state, double *unused, double *out_4279729730729153118);
void car_h_24(double *state, double *unused, double *out_7632868272580967156);
void car_H_24(double *state, double *unused, double *out_2107080131723653552);
void car_h_30(double *state, double *unused, double *out_7903892110822831784);
void car_H_30(double *state, double *unused, double *out_6798062689236401745);
void car_h_26(double *state, double *unused, double *out_901129407029766005);
void car_H_26(double *state, double *unused, double *out_538226411855096894);
void car_h_27(double *state, double *unused, double *out_2953178957272012726);
void car_H_27(double *state, double *unused, double *out_4623299377435976834);
void car_h_29(double *state, double *unused, double *out_684270570982009624);
void car_H_29(double *state, double *unused, double *out_7308294033550793929);
void car_h_28(double *state, double *unused, double *out_4120922758348154463);
void car_H_28(double *state, double *unused, double *out_2225895016481263355);
void car_h_31(double *state, double *unused, double *out_6630208372348191593);
void car_H_31(double *state, double *unused, double *out_87981690378254582);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}