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
void car_err_fun(double *nom_x, double *delta_x, double *out_4191231468621882354);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_4409511713992133464);
void car_H_mod_fun(double *state, double *out_7704822479144562897);
void car_f_fun(double *state, double dt, double *out_2423168834336223124);
void car_F_fun(double *state, double dt, double *out_7639588574330807467);
void car_h_25(double *state, double *unused, double *out_4973933158632202337);
void car_H_25(double *state, double *unused, double *out_1488365746767674340);
void car_h_24(double *state, double *unused, double *out_8075656837058392290);
void car_H_24(double *state, double *unused, double *out_688848676839475633);
void car_h_30(double *state, double *unused, double *out_4816746490281073192);
void car_H_30(double *state, double *unused, double *out_1029967211739574287);
void car_h_26(double *state, double *unused, double *out_2119428105077637665);
void car_H_26(double *state, double *unused, double *out_5229869065641730564);
void car_h_27(double *state, double *unused, double *out_2161381055362348954);
void car_H_27(double *state, double *unused, double *out_3253561282923517504);
void car_h_29(double *state, double *unused, double *out_2436575117646854843);
void car_H_29(double *state, double *unused, double *out_1540198556053966471);
void car_h_28(double *state, double *unused, double *out_7163054323023194599);
void car_H_28(double *state, double *unused, double *out_3542200461015564103);
void car_h_31(double *state, double *unused, double *out_1389660819669613524);
void car_H_31(double *state, double *unused, double *out_1457719784890713912);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}