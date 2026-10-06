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
void car_err_fun(double *nom_x, double *delta_x, double *out_247523503550074134);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8641863619057206531);
void car_H_mod_fun(double *state, double *out_8728310174040499930);
void car_f_fun(double *state, double dt, double *out_3958763527911310895);
void car_F_fun(double *state, double dt, double *out_5830504926638836462);
void car_h_25(double *state, double *unused, double *out_8626650316087834658);
void car_H_25(double *state, double *unused, double *out_5205329524051008253);
void car_h_24(double *state, double *unused, double *out_6473544106049484208);
void car_H_24(double *state, double *unused, double *out_1647403925248685117);
void car_h_30(double *state, double *unused, double *out_3906360730950968585);
void car_H_30(double *state, double *unused, double *out_2686996565543759626);
void car_h_26(double *state, double *unused, double *out_8141341825344733885);
void car_H_26(double *state, double *unused, double *out_8946832842925064477);
void car_h_27(double *state, double *unused, double *out_8023334431411357141);
void car_H_27(double *state, double *unused, double *out_463402494359816409);
void car_h_29(double *state, double *unused, double *out_3652574415947843539);
void car_H_29(double *state, double *unused, double *out_2176765221229367442);
void car_h_28(double *state, double *unused, double *out_7819004321489496824);
void car_H_28(double *state, double *unused, double *out_7259164238298898016);
void car_h_31(double *state, double *unused, double *out_5578923042988477975);
void car_H_31(double *state, double *unused, double *out_5174683562174047825);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}