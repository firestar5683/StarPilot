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
void car_err_fun(double *nom_x, double *delta_x, double *out_8684748936880432144);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_7066640499286813002);
void car_H_mod_fun(double *state, double *out_3671072297043774273);
void car_f_fun(double *state, double dt, double *out_1095605561286512170);
void car_F_fun(double *state, double dt, double *out_5423923306597119811);
void car_h_25(double *state, double *unused, double *out_4540217825902980379);
void car_H_25(double *state, double *unused, double *out_148091647054282596);
void car_h_24(double *state, double *unused, double *out_5565314556450199993);
void car_H_24(double *state, double *unused, double *out_3409833951748040540);
void car_h_30(double *state, double *unused, double *out_1626896214068153924);
void car_H_30(double *state, double *unused, double *out_4675787977181890794);
void car_h_26(double *state, double *unused, double *out_3111249835438660006);
void car_H_26(double *state, double *unused, double *out_3889594965928338820);
void car_h_27(double *state, double *unused, double *out_8904852980145725592);
void car_H_27(double *state, double *unused, double *out_2452193905997947577);
void car_h_29(double *state, double *unused, double *out_5267403451891703242);
void car_H_29(double *state, double *unused, double *out_4165556632867498610);
void car_h_28(double *state, double *unused, double *out_3903179712484879947);
void car_H_28(double *state, double *unused, double *out_2201926361302172359);
void car_h_31(double *state, double *unused, double *out_5990849218531863546);
void car_H_31(double *state, double *unused, double *out_4515803068161690296);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}