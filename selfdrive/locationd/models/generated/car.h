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
void car_err_fun(double *nom_x, double *delta_x, double *out_4276335218073679407);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3738278089596769997);
void car_H_mod_fun(double *state, double *out_8858046684809825962);
void car_f_fun(double *state, double dt, double *out_2600173016712354575);
void car_F_fun(double *state, double dt, double *out_2418560584693982231);
void car_h_25(double *state, double *unused, double *out_7368322694207597671);
void car_H_25(double *state, double *unused, double *out_2361023724919796011);
void car_h_24(double *state, double *unused, double *out_3157655832268166165);
void car_H_24(double *state, double *unused, double *out_1890566242876457287);
void car_h_30(double *state, double *unused, double *out_3617862615253065620);
void car_H_30(double *state, double *unused, double *out_2166672605207812187);
void car_h_26(double *state, double *unused, double *out_5806150257954055878);
void car_H_26(double *state, double *unused, double *out_1380479593954260213);
void car_h_27(double *state, double *unused, double *out_8727950225216967499);
void car_H_27(double *state, double *unused, double *out_56921465976131030);
void car_h_29(double *state, double *unused, double *out_2947958622142233181);
void car_H_29(double *state, double *unused, double *out_1656441260893420003);
void car_h_28(double *state, double *unused, double *out_8124634340540489982);
void car_H_28(double *state, double *unused, double *out_6738840277962950577);
void car_h_31(double *state, double *unused, double *out_5966358236057140703);
void car_H_31(double *state, double *unused, double *out_2391669686796756439);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}