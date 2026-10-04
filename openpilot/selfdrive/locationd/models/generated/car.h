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
void car_err_fun(double *nom_x, double *delta_x, double *out_5329235690424269818);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_7042239097531323453);
void car_H_mod_fun(double *state, double *out_2752254269287091020);
void car_f_fun(double *state, double dt, double *out_2793650179421741975);
void car_F_fun(double *state, double dt, double *out_6729394396829861715);
void car_h_25(double *state, double *unused, double *out_8416223701982646454);
void car_H_25(double *state, double *unused, double *out_6275234919276582697);
void car_h_24(double *state, double *unused, double *out_3705618372733553650);
void car_H_24(double *state, double *unused, double *out_1528725592310073663);
void car_h_30(double *state, double *unused, double *out_3259685145376554226);
void car_H_30(double *state, double *unused, double *out_5254818812941352164);
void car_h_26(double *state, double *unused, double *out_4427428946452695963);
void car_H_26(double *state, double *unused, double *out_6932088983386894601);
void car_h_27(double *state, double *unused, double *out_3414550434321800809);
void car_H_27(double *state, double *unused, double *out_3971132660332917716);
void car_h_29(double *state, double *unused, double *out_447133042106700843);
void car_H_29(double *state, double *unused, double *out_6656127316447734811);
void car_h_28(double *state, double *unused, double *out_1207635595134307505);
void car_H_28(double *state, double *unused, double *out_8619757588013061062);
void car_h_31(double *state, double *unused, double *out_652958445161974013);
void car_H_31(double *state, double *unused, double *out_6305880881153543125);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}