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
void car_err_fun(double *nom_x, double *delta_x, double *out_6883645272193254700);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_7270792730127520500);
void car_H_mod_fun(double *state, double *out_6693185596112580113);
void car_f_fun(double *state, double dt, double *out_8543617912068228194);
void car_F_fun(double *state, double dt, double *out_1180522696706183383);
void car_h_25(double *state, double *unused, double *out_6701820119749264759);
void car_H_25(double *state, double *unused, double *out_8659540204804574995);
void car_h_24(double *state, double *unused, double *out_1034044246016650253);
void car_H_24(double *state, double *unused, double *out_568524981264620230);
void car_h_30(double *state, double *unused, double *out_3064370591495242409);
void car_H_30(double *state, double *unused, double *out_5259507538777368423);
void car_h_26(double *state, double *unused, double *out_4370772842933458404);
void car_H_26(double *state, double *unused, double *out_6045700550030920397);
void car_h_27(double *state, double *unused, double *out_2094489344516732381);
void car_H_27(double *state, double *unused, double *out_3084744226976943512);
void car_h_29(double *state, double *unused, double *out_1937302676165603236);
void car_H_29(double *state, double *unused, double *out_5769738883091760607);
void car_h_28(double *state, double *unused, double *out_6887479827490108384);
void car_H_28(double *state, double *unused, double *out_687339866022230033);
void car_h_31(double *state, double *unused, double *out_3863651303206237672);
void car_H_31(double *state, double *unused, double *out_5419492447797568921);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}