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
void car_err_fun(double *nom_x, double *delta_x, double *out_694062864366320957);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_7656216431051591408);
void car_H_mod_fun(double *state, double *out_2454126163912067491);
void car_f_fun(double *state, double dt, double *out_1843607112126961388);
void car_F_fun(double *state, double dt, double *out_2182262497468252920);
void car_h_25(double *state, double *unused, double *out_4798003278786560335);
void car_H_25(double *state, double *unused, double *out_7357817989096732331);
void car_h_24(double *state, double *unused, double *out_6970490004472512085);
void car_H_24(double *state, double *unused, double *out_1156785309245570905);
void car_h_30(double *state, double *unused, double *out_3972351172998717479);
void car_H_30(double *state, double *unused, double *out_7228479041953492261);
void car_h_26(double *state, double *unused, double *out_1029322094662128166);
void car_H_26(double *state, double *unused, double *out_3616314670222676107);
void car_h_27(double *state, double *unused, double *out_9195955360068189347);
void car_H_27(double *state, double *unused, double *out_5053715730153067350);
void car_h_29(double *state, double *unused, double *out_9038768691717060202);
void car_H_29(double *state, double *unused, double *out_3340353003283516317);
void car_h_28(double *state, double *unused, double *out_4249115445980516624);
void car_H_28(double *state, double *unused, double *out_5303983274848842568);
void car_h_31(double *state, double *unused, double *out_5644913485036226869);
void car_H_31(double *state, double *unused, double *out_7388463950973692759);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}