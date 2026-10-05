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
void car_err_fun(double *nom_x, double *delta_x, double *out_6226893299276424900);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3929429382952821600);
void car_H_mod_fun(double *state, double *out_1271629825232555869);
void car_f_fun(double *state, double dt, double *out_6661690039012274114);
void car_F_fun(double *state, double dt, double *out_1834203406066241770);
void car_h_25(double *state, double *unused, double *out_1060401645907473267);
void car_H_25(double *state, double *unused, double *out_7492528034826712728);
void car_h_24(double *state, double *unused, double *out_8639369439479545960);
void car_H_24(double *state, double *unused, double *out_8239110267165924544);
void car_h_30(double *state, double *unused, double *out_7831236872257824203);
void car_H_30(double *state, double *unused, double *out_4037525697391222133);
void car_h_26(double *state, double *unused, double *out_8434552756934301720);
void car_H_26(double *state, double *unused, double *out_7649690069122038287);
void car_h_27(double *state, double *unused, double *out_3941271621753372378);
void car_H_27(double *state, double *unused, double *out_6212289009191647044);
void car_h_29(double *state, double *unused, double *out_7578721150007394728);
void car_H_29(double *state, double *unused, double *out_7925651736061198077);
void car_h_28(double *state, double *unused, double *out_2997761768851709943);
void car_H_28(double *state, double *unused, double *out_5438693320578822965);
void car_h_31(double *state, double *unused, double *out_390229746721409900);
void car_H_31(double *state, double *unused, double *out_7523173996703673156);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}