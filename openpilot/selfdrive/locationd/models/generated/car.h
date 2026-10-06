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
void car_err_fun(double *nom_x, double *delta_x, double *out_109358598230941622);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_4805958646442115899);
void car_H_mod_fun(double *state, double *out_7514405629275931205);
void car_f_fun(double *state, double dt, double *out_673922476338472781);
void car_F_fun(double *state, double dt, double *out_2470467678435225330);
void car_h_25(double *state, double *unused, double *out_1981012656746252977);
void car_H_25(double *state, double *unused, double *out_3380974713598466874);
void car_h_24(double *state, double *unused, double *out_6443218583231505463);
void car_H_24(double *state, double *unused, double *out_3851432195641805598);
void car_h_30(double *state, double *unused, double *out_1656436871507769373);
void car_H_30(double *state, double *unused, double *out_3510313660741706944);
void car_h_26(double *state, double *unused, double *out_9091580305936470186);
void car_H_26(double *state, double *unused, double *out_2724120649488154970);
void car_h_27(double *state, double *unused, double *out_3020660610914592668);
void car_H_27(double *state, double *unused, double *out_5685076972542131855);
void car_h_29(double *state, double *unused, double *out_6658110139168615018);
void car_H_29(double *state, double *unused, double *out_3000082316427314760);
void car_h_28(double *state, double *unused, double *out_5961308561092248097);
void car_H_28(double *state, double *unused, double *out_8082481333496845334);
void car_h_31(double *state, double *unused, double *out_8568840583222548140);
void car_H_31(double *state, double *unused, double *out_3350328751721506446);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}