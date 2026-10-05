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
void car_err_fun(double *nom_x, double *delta_x, double *out_3469758484501884827);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_4255984246366508924);
void car_H_mod_fun(double *state, double *out_838313629168922668);
void car_f_fun(double *state, double dt, double *out_3973498408852423807);
void car_F_fun(double *state, double dt, double *out_6994900003842630149);
void car_h_25(double *state, double *unused, double *out_6334052399702442592);
void car_H_25(double *state, double *unused, double *out_7083024403804937137);
void car_h_24(double *state, double *unused, double *out_9073812845593672478);
void car_H_24(double *state, double *unused, double *out_2336515076838428103);
void car_h_30(double *state, double *unused, double *out_436782826647908344);
void car_H_30(double *state, double *unused, double *out_8845386711397365852);
void car_h_26(double *state, double *unused, double *out_2167622494160789307);
void car_H_26(double *state, double *unused, double *out_3341521084930880913);
void car_h_27(double *state, double *unused, double *out_992185163816412029);
void car_H_27(double *state, double *unused, double *out_6621792640213422635);
void car_h_29(double *state, double *unused, double *out_5174928876154722274);
void car_H_29(double *state, double *unused, double *out_8335155367082973668);
void car_h_28(double *state, double *unused, double *out_5993858431477257674);
void car_H_28(double *state, double *unused, double *out_5029189689557047374);
void car_h_31(double *state, double *unused, double *out_8152134535960606953);
void car_H_31(double *state, double *unused, double *out_2715312982697529437);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}