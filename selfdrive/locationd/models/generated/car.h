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
void car_err_fun(double *nom_x, double *delta_x, double *out_7751375231448978305);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_1186045100449225538);
void car_H_mod_fun(double *state, double *out_5403210608595880924);
void car_f_fun(double *state, double dt, double *out_3846473641327680019);
void car_F_fun(double *state, double dt, double *out_6505574540477860652);
void car_h_25(double *state, double *unused, double *out_1325906349074366668);
void car_H_25(double *state, double *unused, double *out_693697758010493692);
void car_h_24(double *state, double *unused, double *out_7507130987037302702);
void car_H_24(double *state, double *unused, double *out_2864227840791829444);
void car_h_30(double *state, double *unused, double *out_6134652415174521657);
void car_H_30(double *state, double *unused, double *out_1824635200496754935);
void car_h_26(double *state, double *unused, double *out_3515782194269032819);
void car_H_26(double *state, double *unused, double *out_4435201076884549916);
void car_h_27(double *state, double *unused, double *out_5073135168339482478);
void car_H_27(double *state, double *unused, double *out_4048229271680698152);
void car_h_29(double *state, double *unused, double *out_9171438466618854342);
void car_H_29(double *state, double *unused, double *out_2334866544811147119);
void car_h_28(double *state, double *unused, double *out_6016645021241144913);
void car_H_28(double *state, double *unused, double *out_2747532472258383455);
void car_h_31(double *state, double *unused, double *out_2311543179179655682);
void car_H_31(double *state, double *unused, double *out_5061409179117901392);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}