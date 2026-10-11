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
void car_err_fun(double *nom_x, double *delta_x, double *out_505673110852134299);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6882414693674412674);
void car_H_mod_fun(double *state, double *out_7704283056742914524);
void car_f_fun(double *state, double dt, double *out_805026565951573056);
void car_F_fun(double *state, double dt, double *out_4749317775827675729);
void car_h_25(double *state, double *unused, double *out_5457839146770041094);
void car_H_25(double *state, double *unused, double *out_8041768441628026604);
void car_h_24(double *state, double *unused, double *out_7008468248151095265);
void car_H_24(double *state, double *unused, double *out_623376807951099711);
void car_h_30(double *state, double *unused, double *out_4076126567568063137);
void car_H_30(double *state, double *unused, double *out_8171107388771266674);
void car_h_26(double *state, double *unused, double *out_5964960686497261826);
void car_H_26(double *state, double *unused, double *out_6663472313207468788);
void car_h_27(double *state, double *unused, double *out_5553761492510809709);
void car_H_27(double *state, double *unused, double *out_8100873373137860031);
void car_h_29(double *state, double *unused, double *out_1906797271738078616);
void car_H_29(double *state, double *unused, double *out_6387510646268308998);
void car_h_28(double *state, double *unused, double *out_4194133961501439881);
void car_H_28(double *state, double *unused, double *out_8351140917833635249);
void car_h_31(double *state, double *unused, double *out_1312996079580309842);
void car_H_31(double *state, double *unused, double *out_8011122479751066176);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}