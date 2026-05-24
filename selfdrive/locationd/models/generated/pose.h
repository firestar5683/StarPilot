#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_8958383251573640);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3510167321874192836);
void pose_H_mod_fun(double *state, double *out_10314592692584858);
void pose_f_fun(double *state, double dt, double *out_3469176563342886468);
void pose_F_fun(double *state, double dt, double *out_6053143964145098388);
void pose_h_4(double *state, double *unused, double *out_4331217932147478278);
void pose_H_4(double *state, double *unused, double *out_3761492617151322714);
void pose_h_10(double *state, double *unused, double *out_1904703987337421912);
void pose_H_10(double *state, double *unused, double *out_4366147958481579120);
void pose_h_13(double *state, double *unused, double *out_9149454562438237975);
void pose_H_13(double *state, double *unused, double *out_6973766442483655515);
void pose_h_14(double *state, double *unused, double *out_1095581425659281568);
void pose_H_14(double *state, double *unused, double *out_678704184855950418);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}