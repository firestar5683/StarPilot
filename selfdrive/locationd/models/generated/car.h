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
void car_err_fun(double *nom_x, double *delta_x, double *out_870685266903427678);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8535551015639214025);
void car_H_mod_fun(double *state, double *out_5722367516210042485);
void car_f_fun(double *state, double dt, double *out_6327711019370239094);
void car_F_fun(double *state, double dt, double *out_334732449615445707);
void car_h_25(double *state, double *unused, double *out_4988354507217303652);
void car_H_25(double *state, double *unused, double *out_3470820709702194752);
void car_h_24(double *state, double *unused, double *out_8320591788748654668);
void car_H_24(double *state, double *unused, double *out_5643470308707694318);
void car_h_30(double *state, double *unused, double *out_6271436662034189635);
void car_H_30(double *state, double *unused, double *out_952487751194946125);
void car_h_26(double *state, double *unused, double *out_628706790953232800);
void car_H_26(double *state, double *unused, double *out_7212324028576250976);
void car_h_27(double *state, double *unused, double *out_7592759828026001303);
void car_H_27(double *state, double *unused, double *out_5774922968645859733);
void car_h_29(double *state, double *unused, double *out_7749946496377130448);
void car_H_29(double *state, double *unused, double *out_7488285695515410766);
void car_h_28(double *state, double *unused, double *out_1346308770565827835);
void car_H_28(double *state, double *unused, double *out_5524655423950084515);
void car_h_31(double *state, double *unused, double *out_2214861449768682318);
void car_H_31(double *state, double *unused, double *out_7838532130809602452);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}